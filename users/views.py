from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import get_object_or_404, redirect, render

from platform_admin.models import Client
from platform_admin.services import resolve_company_membership


def login_view(request, company_slug=None, login_mode="workspace"):
    if request.user.is_authenticated and request.session.get("portal_authenticated"):
        if request.user.is_superuser:
            return redirect("platform_admin_dashboard")
        if login_mode == "platform_admin":
            logout(request)
        else:
            return redirect("company_admin_dashboard" if login_mode == "company_admin" else "dashboard")

    company = get_object_or_404(Client, slug=company_slug, is_active=True) if company_slug else getattr(request, "current_client", None)
    error = ""
    email = ""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        User = get_user_model()
        user_record = User.objects.filter(email__iexact=email, is_active=True).first()
        if user_record is None:
            user_record = User.objects.filter(username__iexact=email, is_active=True).first()
        user = authenticate(request, username=user_record.username, password=password) if user_record else None
        if user:
            if login_mode == "platform_admin" and not user.is_superuser:
                error = "This login is restricted to platform super administrators."
                user = None

            membership = None
            membership_error = ""
            if user and login_mode != "platform_admin":
                membership, membership_error = resolve_company_membership(user, company=company)
                if membership and login_mode == "company_admin" and membership.role != "admin":
                    membership = None
                    membership_error = "This login is restricted to company administrators."

            if user and login_mode == "platform_admin":
                login(request, user)
                request.session.cycle_key()
                request.session["portal_user"] = user.get_full_name() or user.email or user.username
                request.session["portal_is_platform_admin"] = True
                request.session["portal_authenticated"] = True
                return redirect("platform_admin_dashboard")

            if membership:
                company = membership.company
                login(request, user)
                request.session.cycle_key()
                request.session["active_client_slug"] = company.slug
                request.session["portal_language"] = company.default_language
                request.session["portal_currency"] = company.default_currency
                request.session["portal_user"] = user.get_full_name() or user.email or user.username
                request.session["portal_role"] = membership.role
                request.session["portal_is_platform_admin"] = bool(user.is_superuser)
                request.session["portal_authenticated"] = True
                destination = "company_admin_dashboard" if login_mode == "company_admin" else "dashboard"
                return redirect("platform_admin_dashboard" if user.is_superuser else destination)
            if user:
                error = membership_error
        if not user and not error:
            error = "Invalid email or password."

    return render(request, "users/login.html", {
        "error": error,
        "email": email,
        "login_company": company,
        "login_mode": login_mode,
    })


def platform_admin_login(request):
    return login_view(request, login_mode="platform_admin")


def company_admin_login(request, company_slug=None):
    return login_view(request, company_slug=company_slug, login_mode="company_admin")


def logout_view(request):
    logout(request)
    return redirect("login")
