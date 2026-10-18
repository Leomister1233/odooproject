import re

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordRecoveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="recover@example.com",
            email="recover@example.com",
            password="old-secure-password",
        )

    def test_login_page_links_to_password_recovery(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, reverse("password_reset"))

    def test_reset_request_does_not_disclose_unknown_email(self):
        known = self.client.post(reverse("password_reset"), {"email": self.user.email})
        unknown = self.client.post(reverse("password_reset"), {"email": "unknown@example.com"})
        self.assertRedirects(known, reverse("password_reset_done"), fetch_redirect_response=False)
        self.assertRedirects(unknown, reverse("password_reset_done"), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)

    def test_user_can_complete_password_reset(self):
        self.client.post(reverse("password_reset"), {"email": self.user.email})
        reset_path = re.search(r"http://testserver(/password-reset/[^\s]+)", mail.outbox[0].body).group(1)
        confirm_response = self.client.get(reset_path)
        self.assertEqual(confirm_response.status_code, 302)
        set_password_path = confirm_response.url
        response = self.client.post(set_password_path, {
            "new_password1": "new-enterprise-password-2026",
            "new_password2": "new-enterprise-password-2026",
        })
        self.assertRedirects(response, reverse("password_reset_complete"), fetch_redirect_response=False)
        self.assertIsNotNone(authenticate(username=self.user.username, password="new-enterprise-password-2026"))
