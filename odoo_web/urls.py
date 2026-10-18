from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("", include("users.urls")),
    path("", include("accounting.urls")),
    path("", include("inventory.urls")),
    path("", include("platform_admin.urls")),
    path("", include("fiscal.urls")),
]

handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
