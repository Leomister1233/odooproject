from decimal import Decimal


def decimal_text(value):
    return format(Decimal(str(value or 0)).quantize(Decimal("0.01")), "f")


def map_odoo_invoice(invoice, configuration):
    partner = invoice.get("partner") or {}
    lines = []
    for index, line in enumerate(invoice.get("lines") or [], start=1):
        lines.append({
            "lineNumber": index,
            "description": line.get("description") or "",
            "quantity": decimal_text(line.get("quantity")),
            "unitPrice": decimal_text(line.get("unit_price")),
            "taxAmount": decimal_text(line.get("tax_amount")),
            "lineTotal": decimal_text(line.get("total")),
        })
    return {
        "schemaVersion": configuration.schema_version,
        "software": {
            "productId": configuration.product_id,
            "productVersion": configuration.product_version,
            "validationNumber": configuration.software_validation_number,
        },
        "issuer": {"taxpayerNumber": configuration.taxpayer_number, "establishment": configuration.establishment_code},
        "customer": {"name": partner.get("name") or "", "taxpayerNumber": partner.get("vat") or ""},
        "document": {
            "odooId": invoice.get("id"),
            "type": invoice.get("document_type") or "FT",
            "number": invoice.get("number") or "",
            "date": str(invoice.get("date") or ""),
            "currency": invoice.get("currency") or "AOA",
            "lines": lines,
            "totals": {
                "net": decimal_text(invoice.get("amount_untaxed")),
                "tax": decimal_text(invoice.get("amount_tax")),
                "gross": decimal_text(invoice.get("amount_total")),
            },
        },
    }
