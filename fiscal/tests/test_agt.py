from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from fiscal.agt.config import AGTSettings
from fiscal.agt.errors import AGTConfigurationError
from fiscal.agt.signing import sign_payload, verify_payload
from fiscal.models import FiscalConfiguration, FiscalEvent, OutboxEvent
from fiscal.services.issuance import prepare_fiscal_document
from platform_admin.models import Client


class AGTStructureTests(TestCase):
    def setUp(self):
        self.company = Client.objects.create(name="Test Company", slug="test-company")
        self.config = FiscalConfiguration.objects.create(company=self.company, taxpayer_number="5000000000", product_id="portal", product_version="1.0")

    @override_settings(AGT_SUBMISSIONS_ENABLED=False)
    def test_submissions_are_disabled_by_default(self):
        with self.assertRaises(AGTConfigurationError):
            AGTSettings.load().validate_for_submission()

    def test_rs256_round_trip_uses_ephemeral_key(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        public_pem = private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        payload = {"document": {"number": "FT 2026/1"}}
        self.assertEqual(verify_payload(sign_payload(payload, private_pem, "test-key"), public_pem), payload)

    def test_preparation_creates_snapshot_outbox_and_audit(self):
        user = get_user_model().objects.create_user("accountant")
        invoice = {"id": 42, "number": "FT 2026/1", "date": "2026-10-18", "amount_untaxed": "100", "amount_tax": "14", "amount_total": "114", "lines": [{"description": "Service", "quantity": 1, "unit_price": 100, "tax_amount": 14, "total": 114}]}
        document = prepare_fiscal_document(company=self.company, odoo_invoice=invoice, actor=user)
        self.assertEqual(document.snapshot["document"]["number"], "FT 2026/1")
        self.assertTrue(OutboxEvent.objects.filter(document=document).exists())
        self.assertTrue(FiscalEvent.objects.filter(document=document, action="prepared").exists())
