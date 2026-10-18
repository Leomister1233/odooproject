from .services import build_navigation_for_client


def platform_context(request):
    client = getattr(request, "current_client", None)
    is_platform_admin = bool(request.user.is_authenticated and request.user.is_superuser)
    company_is_admin = False
    membership = None
    if request.user.is_authenticated and client:
        membership = request.user.company_memberships.filter(
            company=client,
            is_active=True,
        ).first()
        company_is_admin = bool(membership and membership.role == "admin" and not is_platform_admin)

    navigation = build_navigation_for_client(client, request.path)
    if is_platform_admin:
        navigation = [{
            "label": "Platform Administration",
            "items": [
                {"href": "/platform-admin", "icon_name": "overview", "title": "Overview", "meta": "Platform summary", "is_active": request.path == "/platform-admin"},
                {"href": "/platform-admin/companies", "icon_name": "companies", "title": "Companies", "meta": "Client registry", "is_active": request.path.startswith("/platform-admin/companies")},
                {"href": "/platform-admin/users", "icon_name": "users", "title": "Users", "meta": "Company memberships", "is_active": request.path == "/platform-admin/users"},
                {"href": "/platform-admin/features", "icon_name": "features", "title": "Features", "meta": "Feature controls", "is_active": request.path == "/platform-admin/features"},
                {"href": "/platform-admin/releases", "icon_name": "releases", "title": "Releases", "meta": "Version management", "is_active": request.path == "/platform-admin/releases"},
                {"href": "/platform-admin/settings", "icon_name": "settings", "title": "Settings", "meta": "Platform configuration", "is_active": request.path == "/platform-admin/settings"},
            ],
        }]
    elif company_is_admin:
        navigation = [{
            "label": "Company Administration",
            "items": [{
                "href": "/company-admin",
                "icon_name": "overview",
                "title": "Company Admin",
                "meta": "Users and Odoo configuration",
                "is_active": request.path == "/company-admin",
            }],
        }]
    else:
        allowed_modules = {
            "accountant": {"core", "accounting", "fiscal"},
            "warehouse": {"inventory"},
            "viewer": {"core", "accounting", "inventory", "fiscal"},
        }.get(getattr(membership, "role", ""), set())
        navigation = [
            {
                **section,
                "items": [item for item in section["items"] if item.get("module") in allowed_modules],
            }
            for section in navigation
        ]
        navigation = [section for section in navigation if section["items"]]

    return {
        "current_client": client,
        "client_navigation": navigation,
        "platform_is_admin": is_platform_admin,
        "company_is_admin": company_is_admin,
        "portal_role": "platform_admin" if is_platform_admin else getattr(membership, "role", ""),
    }

