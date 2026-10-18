from django.db import models
from django.contrib.auth import get_user_model

from .security import decrypt_secret, encrypt_secret


class Client(models.Model):
    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("pt", "Portuguese"),
    )
    CURRENCY_CHOICES = (
        ("EUR", "Euro"),
        ("USD", "US Dollar"),
        ("AOA", "Angolan Kwanza"),
    )

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    domain = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    template_version = models.CharField(max_length=40, default="v1")
    default_language = models.CharField(max_length=8, choices=LANGUAGE_CHOICES, default="en")
    default_currency = models.CharField(max_length=8, choices=CURRENCY_CHOICES, default="EUR")
    odoo_url = models.CharField(max_length=255, blank=True)
    odoo_db = models.CharField(max_length=255, blank=True)
    odoo_username = models.CharField(max_length=255, blank=True)
    odoo_password = models.CharField(max_length=255, blank=True, default="")
    odoo_password_encrypted = models.TextField(blank=True, default="")
    odoo_company = models.CharField(max_length=255, blank=True)
    primary_color = models.CharField(max_length=20, blank=True, default="#0f172a")
    accent_color = models.CharField(max_length=20, blank=True, default="#7c3aed")
    logo_url = models.URLField(blank=True)
    login_title = models.CharField(max_length=160, blank=True)
    login_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "platform_company"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def set_odoo_password(self, raw_password):
        raw_password = str(raw_password or "").strip()
        if not raw_password:
            return
        self.odoo_password_encrypted = encrypt_secret(raw_password)
        self.odoo_password = ""

    def get_odoo_password(self):
        if self.odoo_password_encrypted:
            try:
                return decrypt_secret(self.odoo_password_encrypted)
            except Exception:
                return ""
        return self.odoo_password

    @property
    def has_stored_odoo_password(self):
        return bool(self.odoo_password_encrypted or self.odoo_password)


class FeatureFlag(models.Model):
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    module = models.CharField(max_length=60)
    description = models.TextField(blank=True)
    default_enabled = models.BooleanField(default=True)
    nav_href = models.CharField(max_length=255, blank=True)
    nav_icon = models.CharField(max_length=60, blank=True)
    nav_title = models.CharField(max_length=120, blank=True)
    nav_meta = models.CharField(max_length=160, blank=True)
    nav_section = models.CharField(max_length=60, blank=True)
    nav_match_prefix = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["module", "sort_order", "name"]

    def __str__(self):
        return self.name


class ClientFeature(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="feature_overrides")
    feature = models.ForeignKey(FeatureFlag, on_delete=models.CASCADE, related_name="client_overrides")
    is_enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("client", "feature")
        ordering = ["feature__sort_order", "feature__name"]

    def __str__(self):
        return f"{self.client.slug}:{self.feature.key}"


class CompanyMembership(models.Model):
    ROLE_CHOICES = (
        ("admin", "Company administrator"),
        ("accountant", "Accountant"),
        ("warehouse", "Warehouse manager"),
        ("viewer", "Viewer"),
    )

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="company_memberships")
    company = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="viewer")
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    is_platform_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "platform_company_membership"
        ordering = ["company__name", "user__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company"],
                name="unique_user_company_membership",
            )
        ]

    def __str__(self):
        return f"{self.user.username}:{self.company.slug}"

class OdooDatabaseRegistration(models.Model):
    company = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="odoo_databases")
    name = models.CharField(max_length=120, default="Primary Odoo")
    server_url = models.URLField(blank=True, default="")
    database_name = models.CharField(max_length=255)
    username_encrypted = models.TextField(blank=True, default="")
    password_encrypted = models.TextField(blank=True, default="")
    odoo_company = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "platform_odoo_database_registration"
        ordering = ["company__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "database_name"],
                name="unique_company_odoo_database",
            )
        ]

    def __str__(self):
        return f"{self.company.slug}:{self.database_name}"

    def set_credentials(self, username, password=None):
        if username:
            self.username_encrypted = encrypt_secret(str(username).strip())
        if password:
            self.password_encrypted = encrypt_secret(str(password).strip())

    def get_username(self):
        return decrypt_secret(self.username_encrypted) if self.username_encrypted else ""

    def get_password(self):
        return decrypt_secret(self.password_encrypted) if self.password_encrypted else ""


class ClientRelease(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="releases")
    version_label = models.CharField(max_length=60)
    git_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    is_current = models.BooleanField(default=False)
    released_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-released_at"]

    def __str__(self):
        return f"{self.client.slug}:{self.version_label}"
