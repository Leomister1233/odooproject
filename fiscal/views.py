from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from core.pagination import paginate_items
from .models import AGTSubmission, FiscalConfiguration, FiscalDocument


def _company(request):
    return getattr(request, "current_client", None)


def _company_admin(request):
    company = _company(request)
    return request.user.is_superuser or request.user.company_memberships.filter(company=company, role="admin", is_active=True).exists()


@login_required
def document_list(request):
    company = _company(request)
    queryset = FiscalDocument.objects.filter(company=company)
    state = request.GET.get("state", "").strip()
    query = request.GET.get("q", "").strip()
    if state:
        queryset = queryset.filter(state=state)
    if query:
        queryset = queryset.filter(document_number__icontains=query)
    pagination = paginate_items(request, queryset, "fiscal_documents")
    return render(request, "fiscal/document_list.html", {"documents": pagination["items"], "documents_pagination": pagination, "filters": {"state": state, "q": query}})


@login_required
def document_detail(request, document_id):
    document = get_object_or_404(FiscalDocument.objects.prefetch_related("events", "submissions"), pk=document_id, company=_company(request))
    return render(request, "fiscal/document_detail.html", {"document": document})


@login_required
def submission_list(request):
    pagination = paginate_items(request, AGTSubmission.objects.filter(company=_company(request)).select_related("document"), "agt_submissions")
    return render(request, "fiscal/submission_list.html", {"submissions": pagination["items"], "submissions_pagination": pagination})


@login_required
def configuration(request):
    company = _company(request)
    if not _company_admin(request):
        return HttpResponseForbidden("Company administrator access is required.")
    config, _ = FiscalConfiguration.objects.get_or_create(company=company, defaults={"taxpayer_number": ""})
    if request.method == "POST":
        for field in ("taxpayer_number", "establishment_code", "product_id", "product_version", "software_validation_number", "producer_key_reference", "credentials_reference"):
            setattr(config, field, request.POST.get(field, "").strip())
        config.environment = request.POST.get("environment") if request.POST.get("environment") in {"homologation", "production"} else "homologation"
        config.submissions_enabled = request.POST.get("submissions_enabled") == "on"
        config.save()
        messages.success(request, "Fiscal configuration saved.")
        return redirect("fiscal_configuration")
    return render(request, "fiscal/configuration.html", {"fiscal_config": config})

