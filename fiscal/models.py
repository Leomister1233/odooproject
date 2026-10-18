import uuid

from django.conf import settings
from django.db import models


class FiscalState(models.TextChoices):
    PREPARED = "PREPARED", "Prepared"
    QUEUED = "QUEUED", "Queued"
    SUBMITTED = "SUBMITTED", "Submitted"
    PROCESSING = "PROCESSING", "Processing"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN", "Outcome unknown"


class FiscalConfiguration(models.Model):
    ENVIRONMENTS = (("homologation", "Homologation"), ("production", "Production"))
    company = models.OneToOneField("platform_admin.Client", on_delete=models.CASCADE, related_name="fiscal_configuration")
    environment = models.CharField(max_length=20, choices=ENVIRONMENTS, default="homologation")
    taxpayer_number = models.CharField(max_length=40)
    establishment_code = models.CharField(max_length=40, default="1")
    schema_version = models.CharField(max_length=20, default="2.0")
    product_id = models.CharField(max_length=100, blank=True)
    product_version = models.CharField(max_length=40, blank=True)
    software_validation_number = models.CharField(max_length=100, blank=True)
    producer_key_reference = models.CharField(max_length=255, blank=True)
    credentials_reference = models.CharField(max_length=255, blank=True)
    submissions_enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.slug}:{self.environment}"


class FiscalSeries(models.Model):
    company = models.ForeignKey("platform_admin.Client", on_delete=models.CASCADE, related_name="fiscal_series")
    establishment_code = models.CharField(max_length=40)
    document_type = models.CharField(max_length=20)
    year = models.PositiveSmallIntegerField()
    series_code = models.CharField(max_length=40)
    next_number = models.PositiveBigIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("company", "establishment_code", "document_type", "year", "series_code"), name="unique_fiscal_series")]


class FiscalDocument(models.Model):
    company = models.ForeignKey("platform_admin.Client", on_delete=models.PROTECT, related_name="fiscal_documents")
    odoo_invoice_id = models.PositiveBigIntegerField()
    document_type = models.CharField(max_length=20, default="FT")
    document_number = models.CharField(max_length=100)
    state = models.CharField(max_length=24, choices=FiscalState.choices, default=FiscalState.PREPARED)
    snapshot = models.JSONField()
    snapshot_hash = models.CharField(max_length=64)
    signature = models.TextField(blank=True)
    agt_request_id = models.CharField(max_length=255, blank=True)
    errors = models.JSONField(default=list, blank=True)
    original_document = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="corrections")
    issued_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [models.UniqueConstraint(fields=("company", "document_number"), name="unique_company_fiscal_document")]


class AGTSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("platform_admin.Client", on_delete=models.PROTECT, related_name="agt_submissions")
    document = models.ForeignKey(FiscalDocument, on_delete=models.PROTECT, related_name="submissions")
    state = models.CharField(max_length=24, choices=FiscalState.choices, default=FiscalState.QUEUED)
    payload = models.JSONField()
    request_metadata = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)


class SubmissionAttempt(models.Model):
    submission = models.ForeignKey(AGTSubmission, on_delete=models.CASCADE, related_name="attempts")
    attempt_number = models.PositiveSmallIntegerField()
    outcome = models.CharField(max_length=40)
    sanitized_error = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("submission", "attempt_number"), name="unique_submission_attempt")]


class OutboxEvent(models.Model):
    STATES = (("pending", "Pending"), ("processing", "Processing"), ("complete", "Complete"), ("failed", "Failed"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("platform_admin.Client", on_delete=models.PROTECT, related_name="fiscal_outbox_events")
    document = models.ForeignKey(FiscalDocument, on_delete=models.PROTECT, related_name="outbox_events")
    event_type = models.CharField(max_length=80, default="fiscal.document.submit")
    payload = models.JSONField(default=dict)
    state = models.CharField(max_length=20, choices=STATES, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FiscalEvent(models.Model):
    company = models.ForeignKey("platform_admin.Client", on_delete=models.PROTECT, related_name="fiscal_events")
    document = models.ForeignKey(FiscalDocument, null=True, blank=True, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    previous_state = models.CharField(max_length=24, blank=True)
    new_state = models.CharField(max_length=24, blank=True)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
