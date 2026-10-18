from django.urls import path

from .views import (
    activate_client,
    client_detail,
    companies,
    company_admin_dashboard,
    company_create,
    dashboard,
    features,
    releases,
    settings,
    users,
)


urlpatterns = [
    path("platform-admin", dashboard, name="platform_admin_dashboard"),
    path("platform-admin/companies", companies, name="platform_admin_companies"),
    path("platform-admin/companies/create", company_create, name="platform_admin_company_create"),
    path("platform-admin/users", users, name="platform_admin_users"),
    path("platform-admin/features", features, name="platform_admin_features"),
    path("platform-admin/releases", releases, name="platform_admin_releases"),
    path("platform-admin/settings", settings, name="platform_admin_settings"),
    path("platform-admin/<slug:slug>", client_detail, name="platform_admin_client_detail"),
    path("platform-admin/<slug:slug>/activate", activate_client, name="platform_admin_activate_client"),
    path("company-admin", company_admin_dashboard, name="company_admin_dashboard"),
]

