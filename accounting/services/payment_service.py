from datetime import date


class PaymentServiceMixin:
    def get_payments(self, limit=30):
        return self._execute("account.payment", "search_read", [[]], {
            "fields": ["id", "name", "partner_id", "date", "amount", "state", "payment_type", "currency_id"],
            "limit": limit,
            "order": "id desc",
        })

    def register_payment(self, invoice_id, amount):
        invoice = self.get_invoice_detail(invoice_id)
        if not invoice:
            raise Exception("Invoice not found")

        wizard_ctx = {
            "active_model": "account.move",
            "active_ids": [int(invoice_id)],
            "active_id": int(invoice_id),
        }
        wizard_vals = {
            "amount": float(amount),
            "payment_date": str(date.today()),
        }
        wizard_id = self._execute(
            "account.payment.register",
            "create",
            [wizard_vals],
            {"context": wizard_ctx},
        )
        self._execute(
            "account.payment.register",
            "action_create_payments",
            [[wizard_id]],
            {"context": wizard_ctx},
        )
        return wizard_id

    def get_payments_page(self, name=None, partner=None, payment_type=None, state=None,
                          date_from=None, date_to=None, limit=50, offset=0):
        domain = []
        if name:
            domain.append(["name", "ilike", name])
        if partner:
            domain.append(["partner_id.name", "ilike", partner])
        if payment_type:
            domain.append(["payment_type", "=", payment_type])
        if state:
            domain.append(["state", "=", state])
        if date_from:
            domain.append(["date", ">=", date_from])
        if date_to:
            domain.append(["date", "<=", date_to])
        return self._search_page(
            "account.payment", domain,
            ["id", "name", "partner_id", "date", "amount", "state", "payment_type", "currency_id"],
            limit=limit, offset=offset, order="id desc",
        )

    def get_vendor_bills(self, limit=30):
        return self._execute("account.move", "search_read", [[["move_type", "=", "in_invoice"]]], {
            "fields": [
                "id",
                "name",
                "partner_id",
                "invoice_date",
                "invoice_date_due",
                "state",
                "payment_state",
                "amount_total",
                "amount_residual",
                "currency_id",
                "ref",
            ],
            "limit": limit,
            "order": "id desc",
        })

    def get_vendor_bills_page(self, vendor=None, reference=None, state=None, payment_state=None,
                              date_from=None, date_to=None, limit=50, offset=0):
        domain = [["move_type", "=", "in_invoice"]]
        if vendor:
            domain.append(["partner_id.name", "ilike", vendor])
        if reference:
            domain.append(["ref", "ilike", reference])
        if state:
            domain.append(["state", "=", state])
        if payment_state:
            domain.append(["payment_state", "=", payment_state])
        if date_from:
            domain.append(["invoice_date", ">=", date_from])
        if date_to:
            domain.append(["invoice_date", "<=", date_to])
        return self._search_page(
            "account.move", domain,
            ["id", "name", "partner_id", "invoice_date", "invoice_date_due", "state", "payment_state", "amount_total", "amount_residual", "currency_id", "ref"],
            limit=limit, offset=offset, order="id desc",
        )
