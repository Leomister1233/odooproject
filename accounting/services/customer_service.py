class CustomerServiceMixin:
    def get_customers(self, limit=50):
        return self._execute("res.partner", "search_read", [[["customer_rank", ">", 0]]], {
            "fields": ["id", "name", "email", "phone"],
            "limit": limit,
            "order": "id desc",
        })

    def create_customer(self, name, email, phone):
        return self._execute("res.partner", "create", [[{
            "name": name,
            "email": email,
            "phone": phone,
            "customer_rank": 1,
        }]])

    def get_customers_page(self, *, name=None, email=None, phone=None, limit=50, offset=0):
        domain = [["customer_rank", ">", 0]]
        if name:
            domain.append(["name", "ilike", name])
        if email:
            domain.append(["email", "ilike", email])
        if phone:
            domain.append(["phone", "ilike", phone])
        return self._search_page(
            "res.partner", domain, ["id", "name", "email", "phone"],
            limit=limit, offset=offset, order="id desc",
        )

    def get_customer_invoices(self, limit=None):
        kwargs = {
            "fields": [
                "id", "name", "partner_id", "invoice_date", "invoice_date_due",
                "amount_untaxed", "amount_tax", "amount_total", "amount_residual",
                "payment_state", "state", "move_type", "currency_id", "journal_id", "ref"
            ],
            "order": "id desc",
        }
        if limit:
            kwargs["limit"] = limit
        return self._execute("account.move", "search_read", [[["move_type", "=", "out_invoice"]]], kwargs)

    def get_posted_customer_invoices(self, limit=None):
        kwargs = {
            "fields": [
                "id", "name", "partner_id", "invoice_date", "invoice_date_due",
                "amount_untaxed", "amount_tax", "amount_total", "amount_residual",
                "payment_state", "state", "move_type", "currency_id"
            ],
            "order": "id desc",
        }
        if limit:
            kwargs["limit"] = limit
        return self._execute(
            "account.move",
            "search_read",
            [[["move_type", "=", "out_invoice"], ["state", "=", "posted"]]],
            kwargs,
        )

    def get_unpaid_customer_invoices(self, limit=None):
        invoices = self.get_posted_customer_invoices(limit=limit)
        return [inv for inv in invoices if inv.get("payment_state") != "paid"]
