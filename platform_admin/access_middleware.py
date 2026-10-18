from django.shortcuts import redirect, render


PUBLIC_PREFIXES = ("/login", "/logout", "/password-reset", "/language/", "/currency/", "/static/")
INVENTORY_PREFIX = "/inventory"
ACCOUNTING_PREFIXES = (
    "/customers", "/invoices", "/payments", "/vendor-bills",
    "/journal-entries", "/reports", "/fiscal",
)


class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith(PUBLIC_PREFIXES):
            return self.get_response(request)

        user = request.user
        if not user.is_authenticated:
            return redirect("login")

        if path.startswith("/platform-admin"):
            if not user.is_superuser:
                return render(request, "core/errors/403.html", status=403)
            return self.get_response(request)

        if user.is_superuser:
            return redirect("platform_admin_dashboard")

        company = getattr(request, "current_client", None)
        membership = user.company_memberships.filter(company=company, is_active=True).first() if company else None
        role = getattr(membership, "role", "")

        if path.startswith("/company-admin"):
            if role != "admin":
                return render(request, "core/errors/403.html", status=403)
            return self.get_response(request)

        if role == "admin" and path != "/fiscal/settings":
            return redirect("company_admin_dashboard")
        if path in {"/", "/dashboard"} and role == "warehouse":
            return redirect("inventory_dashboard")
        if path.startswith(INVENTORY_PREFIX) and role not in {"warehouse", "viewer"}:
            return render(request, "core/errors/403.html", status=403)
        if path.startswith(ACCOUNTING_PREFIXES) and role not in {"accountant", "viewer"}:
            return render(request, "core/errors/403.html", status=403)
        if role == "viewer" and request.method not in {"GET", "HEAD", "OPTIONS"} and (
            path.startswith(INVENTORY_PREFIX) or path.startswith(ACCOUNTING_PREFIXES)
        ):
            return render(request, "core/errors/403.html", status=403)

        return self.get_response(request)
