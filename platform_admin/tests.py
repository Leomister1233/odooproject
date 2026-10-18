from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from platform_admin.models import Client, OdooDatabaseRegistration
from platform_admin.runtime import reset_active_client, set_active_client
from platform_admin.services import OdooConfigurationError, get_client_odoo_settings


class OdooSettingsResolutionTests(TestCase):
    def setUp(self):
        self.company = Client.objects.create(
            name="Tenant One",
            slug="tenant-one",
            is_active=True,
            odoo_username="company@example.com",
        )
        self.company.set_odoo_password("company-password")
        self.company.save(update_fields=["odoo_password", "odoo_password_encrypted"])

    def test_company_without_registration_does_not_use_environment_fallback(self):
        token = set_active_client(self.company)
        try:
            with self.assertRaisesMessage(OdooConfigurationError, "No active Odoo database is registered"):
                get_client_odoo_settings()
        finally:
            reset_active_client(token)

    @override_settings(ODOO_SHARED_URL="https://shared.odoo.example")
    def test_active_registration_is_the_runtime_source_of_truth(self):
        registration = OdooDatabaseRegistration(
            company=self.company,
            name="Production",
            server_url="",
            database_name="tenant_production",
            is_active=True,
            is_default=True,
        )
        registration.save()

        settings = get_client_odoo_settings(self.company)

        self.assertEqual(settings["url"], "https://shared.odoo.example")
        self.assertEqual(settings["db"], "tenant_production")
        self.assertEqual(settings["username"], "company@example.com")
        self.assertEqual(settings["password"], "company-password")
        self.assertEqual(settings["registration_id"], registration.pk)


class PlatformAdminNavigationTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="platform-admin@example.com",
            email="platform-admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin)

    def test_every_sidebar_destination_renders(self):
        route_names = (
            "platform_admin_dashboard",
            "platform_admin_companies",
            "platform_admin_users",
            "platform_admin_features",
            "platform_admin_releases",
            "platform_admin_settings",
        )
        for route_name in route_names:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="sidebar"')

    def test_unsupported_import_link_is_not_rendered(self):
        response = self.client.get(reverse("platform_admin_dashboard"))
        self.assertNotContains(response, "/platform-admin#imports")

    def test_successful_action_uses_global_feedback(self):
        response = self.client.post(reverse("platform_admin_settings"), {"action": "sync_features"}, follow=True)
        self.assertContains(response, "Action completed")
        self.assertContains(response, 'role="status"')

    def test_failed_action_uses_global_feedback(self):
        response = self.client.post(reverse("platform_admin_company_create"), {})
        self.assertContains(response, "Action failed")
        self.assertContains(response, 'role="alert"')
