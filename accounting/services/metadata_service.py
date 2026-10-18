class MetadataServiceMixin:
    def get_taxes(self, limit=50):
        return self._execute("account.tax", "search_read", [[]], {
            "fields": ["id", "name", "amount", "amount_type", "type_tax_use"],
            "limit": limit,
        })

    def get_sales_journals(self):
        return self._execute("account.journal", "search_read", [[["type", "in", ["sale"]]]], {
            "fields": ["id", "name", "code"],
            "limit": 30,
            "order": "id asc",
        })

    def get_payment_terms(self):
        return self._execute("account.payment.term", "search_read", [[]], {
            "fields": ["id", "name"],
            "limit": 50,
            "order": "id asc",
        })

    def get_products(self, limit=100):
        return self._execute("product.product", "search_read", [[]], {
            "fields": ["id", "name", "list_price"],
            "limit": limit,
            "order": "id desc",
        })

    def get_currencies(self, codes=None, include_inactive=False):
        domain = []
        if codes:
            domain.append(["name", "in", list(codes)])

        return self._execute("res.currency", "search_read", [domain], {
            "fields": ["id", "name", "symbol", "active", "rate"],
            "limit": 50,
            "order": "name asc",
            "context": {"active_test": not include_inactive},
        })

    def get_journal_entries(self, limit=30):
        return self._execute("account.move", "search_read", [[["move_type", "=", "entry"]]], {
            "fields": ["id", "name", "date", "state", "journal_id", "ref", "currency_id", "amount_total"],
            "limit": limit,
            "order": "id desc",
        })

    def get_journal_entries_page(self, name=None, journal_id=None, reference=None, state=None,
                                 date_from=None, date_to=None, limit=50, offset=0):
        domain = [["move_type", "=", "entry"]]
        if name:
            domain.append(["name", "ilike", name])
        if journal_id:
            domain.append(["journal_id", "=", int(journal_id)])
        if reference:
            domain.append(["ref", "ilike", reference])
        if state:
            domain.append(["state", "=", state])
        if date_from:
            domain.append(["date", ">=", date_from])
        if date_to:
            domain.append(["date", "<=", date_to])
        return self._search_page(
            "account.move", domain,
            ["id", "name", "date", "state", "journal_id", "ref", "currency_id", "amount_total"],
            limit=limit, offset=offset, order="id desc",
        )
