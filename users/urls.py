from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from users.views import company_admin_login, login_view, logout_view, platform_admin_login

urlpatterns = [
    path("login/platform-admin", platform_admin_login, name="platform_admin_login"),
    path("login/company-admin", company_admin_login, name="company_admin_login"),
    path("login/company-admin/<slug:company_slug>", company_admin_login, name="company_admin_company_login"),
    path("login", login_view, name="login"),
    path("login/<slug:company_slug>", login_view, name="company_login"),
    path(
        "password-reset",
        auth_views.PasswordResetView.as_view(
            template_name="users/password_reset_form.html",
            email_template_name="users/password_reset_email.txt",
            subject_template_name="users/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path("password-reset/sent", auth_views.PasswordResetDoneView.as_view(template_name="users/password_reset_done.html"), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>", auth_views.PasswordResetConfirmView.as_view(template_name="users/password_reset_confirm.html", success_url=reverse_lazy("password_reset_complete")), name="password_reset_confirm"),
    path("password-reset/complete", auth_views.PasswordResetCompleteView.as_view(template_name="users/password_reset_complete.html"), name="password_reset_complete"),
    path("logout", logout_view, name="logout"),
]
