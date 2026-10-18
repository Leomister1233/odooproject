from decimal import Decimal

from .errors import AGTValidationError


def validate_invoice_payload(payload):
    errors = []
    issuer = payload.get("issuer", {})
    document = payload.get("document", {})
    if not issuer.get("taxpayerNumber"):
        errors.append("Issuer taxpayer number is required.")
    if not document.get("number"):
        errors.append("Document number is required.")
    if not document.get("date"):
        errors.append("Document date is required.")
    if not document.get("lines"):
        errors.append("At least one invoice line is required.")
    totals = document.get("totals", {})
    try:
        if Decimal(totals.get("net", "0")) + Decimal(totals.get("tax", "0")) != Decimal(totals.get("gross", "0")):
            errors.append("Document totals are inconsistent.")
    except Exception:
        errors.append("Document totals must be valid decimal values.")
    if errors:
        raise AGTValidationError(errors)
    return payload
