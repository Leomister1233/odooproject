from datetime import date


class InvoiceServiceMixin:
    def get_invoices(self, state=None, partner_id=None, date_from=None, date_to=None, limit=50):
        domain = [["move_type", "=", "out_invoice"]]
        if state:
            domain.append(["state", "=", state])
        if partner_id:
            domain.append(["partner_id", "=", int(partner_id)])
        if date_from:
            domain.append(["invoice_date", ">=", date_from])
        if date_to:
            domain.append(["invoice_date", "<=", date_to])

        return self._execute("account.move", "search_read", [domain], {
            "fields": ["id", "name", "partner_id", "invoice_date", "invoice_date_due", "state", "payment_state", "amount_total", "amount_residual", "ref", "currency_id", "journal_id"],
            "limit": limit,
            "order": "id desc",
        })

    def get_invoices_page(self, state=None, partner_id=None, date_from=None, date_to=None,
                          reference=None, journal_id=None, payment_state=None, limit=50, offset=0):
        domain = [["move_type", "=", "out_invoice"]]
        if state:
            domain.append(["state", "=", state])
        if partner_id:
            domain.append(["partner_id", "=", int(partner_id)])
        if date_from:
            domain.append(["invoice_date", ">=", date_from])
        if date_to:
            domain.append(["invoice_date", "<=", date_to])
        if reference:
            domain.append(["ref", "ilike", reference])
        if journal_id:
            domain.append(["journal_id", "=", int(journal_id)])
        if payment_state:
            domain.append(["payment_state", "=", payment_state])
        return self._search_page(
            "account.move", domain,
            ["id", "name", "partner_id", "invoice_date", "invoice_date_due", "state", "payment_state", "amount_total", "amount_residual", "ref", "currency_id", "journal_id"],
            limit=limit, offset=offset, order="id desc",
        )

    def get_invoice_detail(self, invoice_id):
        invoice = self._execute("account.move", "read", [[int(invoice_id)]], {
            "fields": [
                "id", "name", "partner_id", "invoice_date", "invoice_date_due",
                "state", "payment_state", "amount_total", "amount_residual",
                "invoice_line_ids", "invoice_origin", "ref", "journal_id",
                "invoice_payment_term_id", "currency_id", "narration"
            ],
        })
        if not invoice:
            return None
        details = invoice[0]
        line_ids = details.get("invoice_line_ids", [])
        lines = []
        if line_ids:
            lines = self._execute("account.move.line", "read", [line_ids], {
                "fields": ["name", "quantity", "price_unit", "price_subtotal", "price_total", "tax_ids", "product_id"],
            })
        details["lines"] = lines
        return details

    def create_invoice(self, partner_id, invoice_date, due_date, reference, journal_id, payment_term_id, line_items):
        if not line_items:
            raise Exception("At least one invoice line is required.")
        invoice_lines = []
        for item in line_items:
            values = {
                "name": item["description"],
                "quantity": float(item["quantity"]),
                "price_unit": float(item["unit_price"]),
            }
            if item.get("product_id"):
                values["product_id"] = int(item["product_id"])
            if item.get("tax_ids"):
                values["tax_ids"] = [[6, 0, [int(tax_id) for tax_id in item["tax_ids"]]]]
            invoice_lines.append([0, 0, values])

        return self._execute("account.move", "create", [[{
            "move_type": "out_invoice",
            "partner_id": int(partner_id),
            "invoice_date": invoice_date or str(date.today()),
            "invoice_date_due": due_date or False,
            "ref": reference or False,
            "journal_id": int(journal_id) if journal_id else False,
            "invoice_payment_term_id": int(payment_term_id) if payment_term_id else False,
            "invoice_line_ids": invoice_lines,
        }]])

    def post_invoice(self, invoice_id):
        return self._execute("account.move", "action_post", [[int(invoice_id)]])

    def get_recent_invoices(self, limit=10):
        return self.get_customer_invoices(limit=limit)
