import hashlib

from django.db import transaction

from fiscal.agt.mapping import map_odoo_invoice
from fiscal.agt.signing import canonical_json
from fiscal.agt.validation import validate_invoice_payload
from fiscal.models import FiscalConfiguration, FiscalDocument, FiscalEvent, FiscalState, OutboxEvent


@transaction.atomic
def prepare_fiscal_document(*, company, odoo_invoice, actor=None):
    configuration = FiscalConfiguration.objects.get(company=company)
    payload = validate_invoice_payload(map_odoo_invoice(odoo_invoice, configuration))
    digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    document, created = FiscalDocument.objects.get_or_create(
        company=company,
        document_number=payload["document"]["number"],
        defaults={
            "odoo_invoice_id": payload["document"]["odooId"],
            "document_type": payload["document"]["type"],
            "snapshot": payload,
            "snapshot_hash": digest,
        },
    )
    if not created and document.snapshot_hash != digest:
        raise ValueError("A fiscal document snapshot cannot be changed after preparation.")
    if created:
        OutboxEvent.objects.create(company=company, document=document, payload={"document_id": document.pk})
        FiscalEvent.objects.create(company=company, document=document, actor=actor, action="prepared", new_state=FiscalState.PREPARED)
    return document

