from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.test import RequestFactory, TestCase
from unittest.mock import patch

from core.pagination import get_page_window, paginate_items, paginate_remote
from platform_admin.models import Client, CompanyMembership


class RoleAccessTests(TestCase):
    def setUp(self):
        self.company = Client.objects.create(name="Test Company", slug="test-company", is_default=True)
        user_model = get_user_model()
        self.superuser = user_model.objects.create_superuser("platform", "platform@example.com", "test-password")
        self.company_admin = self._member("company-admin", "admin")
        self.accountant = self._member("accountant", "accountant")
        self.warehouse = self._member("warehouse", "warehouse")
        self.viewer = self._member("viewer", "viewer")

    def _member(self, username, role):
        user = get_user_model().objects.create_user(username, f"{username}@example.com", "test-password")
        CompanyMembership.objects.create(user=user, company=self.company, role=role, is_active=True, is_default=True)
        return user

    def _login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session["portal_authenticated"] = True
        session["active_client_slug"] = self.company.slug
        session.save()

    def test_anonymous_workspace_redirects_to_login(self):
        self.assertRedirects(self.client.get("/dashboard"), "/login", fetch_redirect_response=False)

    def test_superuser_is_kept_in_platform_context(self):
        self._login(self.superuser)
        self.assertRedirects(self.client.get("/dashboard"), "/platform-admin", fetch_redirect_response=False)

    def test_platform_dashboard_renders_for_superuser(self):
        self._login(self.superuser)
        response = self.client.get("/platform-admin")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Client registry")
        self.assertContains(response, "Recent activity")

    def test_company_admin_is_kept_in_company_context(self):
        self._login(self.company_admin)
        self.assertRedirects(self.client.get("/dashboard"), "/company-admin", fetch_redirect_response=False)

    def test_accountant_cannot_open_inventory(self):
        self._login(self.accountant)
        self.assertEqual(self.client.get("/inventory").status_code, 403)

    def test_warehouse_cannot_open_accounting(self):
        self._login(self.warehouse)
        self.assertEqual(self.client.get("/invoices").status_code, 403)

    def test_warehouse_dashboard_uses_inventory_context(self):
        self._login(self.warehouse)
        self.assertRedirects(self.client.get("/dashboard"), "/inventory", fetch_redirect_response=False)

    def test_company_user_cannot_open_platform_admin(self):
        self._login(self.company_admin)
        self.assertEqual(self.client.get("/platform-admin").status_code, 403)

    @patch("accounting.views.OdooAccountingService", side_effect=RuntimeError("Odoo unavailable"))
    def test_accountant_core_pages_remain_available_when_odoo_is_unavailable(self, _service):
        self._login(self.accountant)
        for path in ("/dashboard", "/customers", "/invoices", "/payments", "/vendor-bills", "/journal-entries", "/reports", "/fiscal/documents", "/fiscal/submissions"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    @patch("inventory.views.OdooInventoryService", side_effect=RuntimeError("Odoo unavailable"))
    def test_warehouse_core_pages_remain_available_when_odoo_is_unavailable(self, _service):
        self._login(self.warehouse)
        for path in ("/inventory", "/inventory/products", "/inventory/stock", "/inventory/transfers", "/inventory/receipts", "/inventory/deliveries", "/inventory/internal-transfers", "/inventory/adjustments", "/inventory/replenishment", "/inventory/locations"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    @patch("accounting.views.OdooAccountingService", side_effect=RuntimeError("Odoo unavailable"))
    def test_accountant_sidebar_exposes_implemented_workflows(self, _service):
        self._login(self.accountant)
        response = self.client.get("/dashboard")
        for path in ("/customers", "/invoices", "/payments", "/vendor-bills", "/journal-entries", "/reports", "/fiscal/documents", "/fiscal/submissions"):
            self.assertContains(response, f'href="{path}"')

    @patch("inventory.views.OdooInventoryService", side_effect=RuntimeError("Odoo unavailable"))
    def test_warehouse_sidebar_exposes_implemented_workflows(self, _service):
        self._login(self.warehouse)
        response = self.client.get("/inventory")
        for path in ("/inventory/products", "/inventory/stock", "/inventory/transfers", "/inventory/locations"):
            self.assertContains(response, f'href="{path}"')

    def test_viewer_is_read_only(self):
        self._login(self.viewer)
        self.assertEqual(self.client.post("/customers", {"name": "Blocked"}).status_code, 403)
        self.assertEqual(self.client.post("/inventory/adjustments", {}).status_code, 403)


class PlatformAdminLoginTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username="platform-owner",
            email="",
            password="admin password",
        )

    def test_superuser_can_login_with_username(self):
        response = self.client.post("/login/platform-admin", {
            "email": "platform-owner",
            "password": "admin password",
        })

        self.assertRedirects(response, "/platform-admin", fetch_redirect_response=False)
        self.assertTrue(self.client.session["portal_authenticated"])
        self.assertTrue(self.client.session["portal_is_platform_admin"])

    def test_platform_login_accepts_non_email_identifier(self):
        response = self.client.get("/login/platform-admin")

        self.assertContains(response, 'type="text"')
        self.assertContains(response, "Email or username")


class PaginationTests(TestCase):
    def test_supported_page_size_is_retained(self):
        request = RequestFactory().get("/records", {"records_page_size": "25"})
        result = paginate_items(request, list(range(60)), "records")
        self.assertEqual(result["page_size"], 25)
        self.assertEqual(len(result["items"]), 25)

    def test_unsupported_page_size_falls_back_to_fifty(self):
        request = RequestFactory().get("/records", {"records_page_size": "200"})
        result = paginate_items(request, list(range(60)), "records")
        self.assertEqual(result["page_size"], 50)

    def test_remote_window_uses_validated_offset(self):
        request = RequestFactory().get("/records", {"records_page": "3", "records_page_size": "25"})
        window = get_page_window(request, "records")
        self.assertEqual(window["offset"], 50)
        result = paginate_remote(request, list(range(10)), 60, "records")
        self.assertEqual(result["start_index"], 51)
        self.assertEqual(result["end_index"], 60)


class TemplateSmokeTests(TestCase):
    def test_redesigned_layouts_and_error_templates_compile(self):
        for name in (
            "core/base.html",
            "core/auth_base.html",
            "users/login.html",
            "platform_admin/dashboard.html",
            "platform_admin/client_detail.html",
            "platform_admin/company_form.html",
            "platform_admin/company_admin.html",
            "platform_admin/section.html",
            "core/errors/403.html",
            "core/errors/404.html",
            "core/errors/500.html",
        ):
            with self.subTest(template=name):
                self.assertIsNotNone(get_template(name))
