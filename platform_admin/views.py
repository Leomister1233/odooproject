from copy import deepcopy

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.conf import settings as django_settings
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.urls import reverse

from core.pagination import paginate_items

from .models import (
    Client,
    ClientFeature,
    ClientRelease,
    CompanyMembership,
    FeatureFlag,
    OdooDatabaseRegistration,
)
from .services import get_client_feature_map, get_client_odoo_settings, sync_feature_catalog, test_odoo_connection


def _protected(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_superuser:
        return HttpResponseForbidden("Platform Admin is restricted to application super administrators.")
    return None


def _client_form_data(client, overrides=None):
    data = {
        "name": client.name,
        "domain": client.domain,
        "template_version": client.template_version,
        "default_language": client.default_language,
        "default_currency": client.default_currency,
        "odoo_url": client.odoo_url,
        "odoo_db": client.odoo_db,
        "odoo_username": client.odoo_username,
        "odoo_company": client.odoo_company,
        "logo_url": client.logo_url,
        "primary_color": client.primary_color,
        "accent_color": client.accent_color,
        "is_active": client.is_active,
        "is_default": client.is_default,
    }
    if overrides:
        data.update(overrides)
    return data


def _posted_client_form_data(request, client):
    return {
        "name": request.POST.get("name", client.name).strip() or client.name,
        "domain": request.POST.get("domain", client.domain).strip(),
        "template_version": request.POST.get("template_version", client.template_version).strip() or client.template_version,
        "default_language": request.POST.get("default_language", client.default_language).strip() or client.default_language,
        "default_currency": request.POST.get("default_currency", client.default_currency).strip() or client.default_currency,
        "odoo_url": request.POST.get("odoo_url", client.odoo_url).strip(),
        "odoo_db": request.POST.get("odoo_db", client.odoo_db).strip(),
        "odoo_username": request.POST.get("odoo_username", client.odoo_username).strip(),
        "odoo_company": request.POST.get("odoo_company", client.odoo_company).strip(),
        "logo_url": request.POST.get("logo_url", client.logo_url).strip(),
        "primary_color": request.POST.get("primary_color", client.primary_color).strip() or client.primary_color,
        "accent_color": request.POST.get("accent_color", client.accent_color).strip() or client.accent_color,
        "is_active": request.POST.get("is_active") == "on",
        "is_default": request.POST.get("is_default") == "on",
    }


def dashboard(request):
    protected = _protected(request)
    if protected:
        return protected

    sync_feature_catalog()

    all_clients = list(
        Client.objects.annotate(
            enabled_overrides=Count("feature_overrides", filter=Q(feature_overrides__is_enabled=True)),
            release_count=Count("releases"),
            member_count=Count("memberships", filter=Q(memberships__is_active=True), distinct=True),
        ).order_by("name")
    )
    clients = all_clients
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    if search_query:
        clients = [client for client in clients if search_query.casefold() in f"{client.name} {client.slug} {client.domain}".casefold()]
    if status_filter == "active":
        clients = [client for client in clients if client.is_active]
    elif status_filter == "archived":
        clients = [client for client in clients if not client.is_active]
    for client in clients:
        client.enabled_feature_count = sum(1 for enabled in get_client_feature_map(client).values() if enabled)

    recent_clients = sorted(all_clients, key=lambda client: client.updated_at, reverse=True)[:5]
    company_pagination = paginate_items(request, clients, "companies")
    return render(request, "platform_admin/dashboard.html", {
        "clients": company_pagination["items"],
        "company_pagination": company_pagination,
        "team_member_count": CompanyMembership.objects.filter(is_active=True).values("user_id").distinct().count(),
        "connected_database_count": OdooDatabaseRegistration.objects.filter(is_active=True).count(),
        "pending_import_count": 0,
        "active_client_count": sum(1 for client in all_clients if client.is_active),
        "recent_clients": recent_clients,
    })


def companies(request):
    return dashboard(request)


def users(request):
    protected = _protected(request)
    if protected:
        return protected
    queryset = CompanyMembership.objects.select_related("user", "company").order_by("company__name", "user__email")
    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(Q(user__email__icontains=query) | Q(user__username__icontains=query) | Q(company__name__icontains=query))
    pagination = paginate_items(request, queryset, "platform_users")
    return render(request, "platform_admin/section.html", {"section": "users", "records": pagination["items"], "pagination": pagination, "query": query})


def features(request):
    protected = _protected(request)
    if protected:
        return protected
    sync_feature_catalog()
    queryset = FeatureFlag.objects.annotate(company_count=Count("client_overrides", filter=Q(client_overrides__is_enabled=True), distinct=True)).order_by("module", "sort_order")
    pagination = paginate_items(request, queryset, "platform_features")
    return render(request, "platform_admin/section.html", {"section": "features", "records": pagination["items"], "pagination": pagination})


def releases(request):
    protected = _protected(request)
    if protected:
        return protected
    queryset = ClientRelease.objects.select_related("client").order_by("-released_at")
    pagination = paginate_items(request, queryset, "platform_releases")
    return render(request, "platform_admin/section.html", {"section": "releases", "records": pagination["items"], "pagination": pagination})


def settings(request):
    protected = _protected(request)
    if protected:
        return protected
    if request.method == "POST" and request.POST.get("action") == "sync_features":
        sync_feature_catalog()
        messages.success(request, "Feature catalogue synchronized.")
        return redirect("platform_admin_settings")
    return render(request, "platform_admin/section.html", {
        "section": "settings",
        "shared_odoo_url": django_settings.ODOO_SHARED_URL,
        "client_count": Client.objects.count(),
        "feature_count": FeatureFlag.objects.count(),
    })


def company_create(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        slug = slugify(request.POST.get("slug", "").strip() or name)
        odoo_email = request.POST.get("odoo_username", "").strip().lower()
        odoo_password = request.POST.get("odoo_password", "")
        if not name or not slug or not odoo_email or not odoo_password:
            error = "Company name, Odoo email, and Odoo password are required."
        elif Client.objects.filter(slug=slug).exists():
            error = "A company with this slug already exists."
        else:
            company = Client.objects.create(
                name=name,
                slug=slug,
                domain=request.POST.get("domain", "").strip(),
                default_language=request.POST.get("default_language", "en"),
                default_currency=request.POST.get("default_currency", "EUR"),
                login_title=request.POST.get("login_title", "").strip(),
                login_message=request.POST.get("login_message", "").strip(),
                odoo_username=odoo_email,
                is_active=True,
            )
            company.set_odoo_password(odoo_password)
            company.save(update_fields=["odoo_password", "odoo_password_encrypted"])
            messages.success(request, "Company created.")
            return redirect("platform_admin_client_detail", slug=company.slug)

    return render(request, "platform_admin/company_form.html", {"error": error})


def client_detail(request, slug):
    protected = _protected(request)
    if protected:
        return protected

    sync_feature_catalog()
    client = get_object_or_404(Client, slug=slug)
    message = ""
    error = ""
    connection_result = None
    settings_form = _client_form_data(client)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        settings_form = _posted_client_form_data(request, client)
        if action == "save_settings":
            client.name = settings_form["name"]
            client.domain = settings_form["domain"]
            client.template_version = settings_form["template_version"]
            client.default_language = settings_form["default_language"]
            client.default_currency = settings_form["default_currency"]
            client.odoo_url = settings_form["odoo_url"]
            client.odoo_db = settings_form["odoo_db"]
            client.odoo_username = settings_form["odoo_username"]
            posted_password = request.POST.get("odoo_password", "").strip()
            if posted_password:
                client.set_odoo_password(posted_password)
            client.odoo_company = settings_form["odoo_company"]
            client.logo_url = settings_form["logo_url"]
            client.primary_color = settings_form["primary_color"]
            client.accent_color = settings_form["accent_color"]
            client.is_active = settings_form["is_active"]
            client.is_default = settings_form["is_default"]
            if client.is_default:
                Client.objects.exclude(pk=client.pk).update(is_default=False)
            client.save()
            message = "Client settings updated."
            settings_form = _client_form_data(client)

        elif action == "test_connection":
            transient_client = deepcopy(client)
            transient_client.name = settings_form["name"]
            transient_client.domain = settings_form["domain"]
            transient_client.template_version = settings_form["template_version"]
            transient_client.default_language = settings_form["default_language"]
            transient_client.default_currency = settings_form["default_currency"]
            transient_client.odoo_url = settings_form["odoo_url"]
            transient_client.odoo_db = settings_form["odoo_db"]
            transient_client.odoo_username = settings_form["odoo_username"]
            transient_client.odoo_company = settings_form["odoo_company"]
            transient_client.logo_url = settings_form["logo_url"]
            transient_client.primary_color = settings_form["primary_color"]
            transient_client.accent_color = settings_form["accent_color"]

            posted_password = request.POST.get("odoo_password", "").strip()
            if posted_password:
                transient_client.set_odoo_password(posted_password)
            try:
                connection_result = test_odoo_connection(get_client_odoo_settings(transient_client))
                message = "Odoo connection succeeded."
            except Exception as exc:
                error = str(exc)

        elif action == "save_features":
            selected_keys = set(request.POST.getlist("feature_keys"))
            for feature in FeatureFlag.objects.all():
                ClientFeature.objects.update_or_create(
                    client=client,
                    feature=feature,
                    defaults={"is_enabled": feature.key in selected_keys},
                )
            message = "Client features updated."

        elif action == "add_release":
            version_label = request.POST.get("version_label", "").strip()
            git_reference = request.POST.get("git_reference", "").strip()
            notes = request.POST.get("notes", "").strip()
            is_current = request.POST.get("is_current") == "on"
            if version_label:
                if is_current:
                    ClientRelease.objects.filter(client=client).update(is_current=False)
                    client.template_version = version_label
                    client.save(update_fields=["template_version"])
                ClientRelease.objects.create(
                    client=client,
                    version_label=version_label,
                    git_reference=git_reference,
                    notes=notes,
                    is_current=is_current,
                )
                message = "Release added."

        elif action == "add_odoo_database":
            database_name = request.POST.get("database_name", "").strip()
            if not database_name:
                error = "Database name is required."
            elif OdooDatabaseRegistration.objects.filter(company=client, database_name=database_name).exists():
                error = "This Odoo database is already registered for the company."
            else:
                is_default = request.POST.get("database_is_default") == "on"
                if is_default:
                    client.odoo_databases.update(is_default=False)
                registration = OdooDatabaseRegistration(
                    company=client,
                    name=request.POST.get("database_label", "").strip() or "Primary Odoo",
                    server_url=django_settings.ODOO_SHARED_URL,
                    database_name=database_name,
                    odoo_company=request.POST.get("database_company", "").strip(),
                    is_active=True,
                    is_default=is_default or not client.odoo_databases.exists(),
                    username_encrypted="",
                    password_encrypted="",
                )
                registration.save()
                message = "Odoo database registered with encrypted credentials."

        elif action == "add_company_user":
            email = request.POST.get("user_email", "").strip().lower()
            password = request.POST.get("user_password", "").strip()
            role = request.POST.get("user_role", "viewer").strip()
            if not email or not password:
                error = "User email and temporary password are required."
            else:
                User = get_user_model()
                user, created = User.objects.get_or_create(
                    username=email,
                    defaults={"email": email, "is_active": True},
                )
                if created or request.POST.get("reset_user_password") == "on":
                    user.set_password(password)
                    user.save(update_fields=["password"])
                CompanyMembership.objects.update_or_create(
                    user=user,
                    company=client,
                    defaults={
                        "role": role,
                        "is_active": True,
                        "is_default": request.POST.get("user_is_default") == "on",
                        "is_platform_admin": False,
                    },
                )
                message = "Company user created and assigned."

        elif action == "toggle_odoo_database":
            registration = get_object_or_404(OdooDatabaseRegistration, pk=request.POST.get("registration_id"), company=client)
            registration.is_active = not registration.is_active
            if request.POST.get("make_default") == "on":
                client.odoo_databases.exclude(pk=registration.pk).update(is_default=False)
                registration.is_default = True
                registration.is_active = True
            registration.save(update_fields=["is_active", "is_default", "updated_at"])
            message = "Odoo database registration updated."

        elif action == "toggle_company_user":
            membership = get_object_or_404(CompanyMembership, pk=request.POST.get("membership_id"), company=client)
            if membership.user == request.user:
                error = "You cannot disable your own platform membership."
            else:
                membership.is_active = not membership.is_active
                membership.save(update_fields=["is_active"])
                message = "Company user membership updated."

        if message and action != "test_connection":
            tab_by_action = {
                "save_settings": "settings",
                "save_features": "features",
                "add_release": "releases",
                "add_odoo_database": "databases",
                "toggle_odoo_database": "databases",
                "add_company_user": "users",
                "toggle_company_user": "users",
            }
            messages.success(request, message)
            return redirect(f"{reverse('platform_admin_client_detail', kwargs={'slug': client.slug})}#{tab_by_action.get(action, 'settings')}")

    feature_map = get_client_feature_map(client)
    features = list(FeatureFlag.objects.order_by("module", "sort_order"))
    releases = list(client.releases.all())
    odoo_databases = list(client.odoo_databases.all())
    memberships = list(client.memberships.select_related("user").all())

    return render(
        request,
        "platform_admin/client_detail.html",
        {
            "client_record": client,
            "features": features,
            "feature_map": feature_map,
            "releases": releases,
            "message": message,
            "error": error,
            "connection_result": connection_result,
            "settings_form": settings_form,
            "odoo_databases": odoo_databases,
            "memberships": memberships,
            "shared_odoo_url": django_settings.ODOO_SHARED_URL,
        },
    )


def activate_client(request, slug):
    protected = _protected(request)
    if protected:
        return protected

    client = get_object_or_404(Client, slug=slug, is_active=True)
    request.session["active_client_slug"] = client.slug
    request.session["portal_language"] = client.default_language
    request.session["portal_currency"] = client.default_currency
    return redirect(request.GET.get("next") or "platform_admin_dashboard")


def company_admin_dashboard(request):
    if not request.user.is_authenticated:
        return redirect("login")

    company = getattr(request, "current_client", None)
    membership = None
    if company:
        membership = CompanyMembership.objects.filter(
            user=request.user,
            company=company,
            is_active=True,
            role="admin",
        ).first()
    if membership is None and not request.user.is_superuser:
        return HttpResponseForbidden("Company administration requires the company administrator role.")
    if company is None:
        return HttpResponseForbidden("No active company is selected.")

    return render(request, "platform_admin/company_admin.html", {
        "company_record": company,
        "memberships": company.memberships.select_related("user").filter(is_active=True),
        "odoo_databases": company.odoo_databases.filter(is_active=True),
    })
