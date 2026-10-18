from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .currency import PORTAL_CURRENCY_CHOICES, get_portal_currency
from .i18n import PORTAL_LANGUAGE_CHOICES, PORTAL_LANGUAGE_DEFAULT, get_portal_language


def error_403(request, exception=None):
    return render(request, "core/errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "core/errors/404.html", status=404)


def error_500(request):
    return render(request, "core/errors/500.html", status=500)


def toggle_language(request: HttpRequest) -> HttpResponseRedirect:
    current_language = get_portal_language(request)
    next_language = "pt" if current_language == PORTAL_LANGUAGE_DEFAULT else PORTAL_LANGUAGE_DEFAULT
    request.session["portal_language"] = next_language

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/dashboard"
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = "/dashboard"

    return redirect(next_url)


def set_language(request: HttpRequest, language_code: str) -> HttpResponseRedirect:
    if language_code in PORTAL_LANGUAGE_CHOICES:
        request.session["portal_language"] = language_code

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/dashboard"
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = "/dashboard"

    return redirect(next_url)


def set_currency(request: HttpRequest, currency_code: str) -> HttpResponseRedirect:
    normalized_currency_code = str(currency_code or "").upper()
    if normalized_currency_code in PORTAL_CURRENCY_CHOICES:
        request.session["portal_currency"] = normalized_currency_code
    else:
        request.session["portal_currency"] = get_portal_currency(request)

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/dashboard"
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = "/dashboard"

    return redirect(next_url)
