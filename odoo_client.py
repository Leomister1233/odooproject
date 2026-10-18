import xmlrpc.client

from platform_admin.services import get_client_odoo_settings


class OdooClient:
    def __init__(self):
        settings = get_client_odoo_settings()
        self.url = settings["url"]
        self.db = settings["db"]
        self.username = settings["username"]
        self.password = settings["password"]

        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

        try:
            self.uid = self.common.authenticate(
                self.db,
                self.username,
                self.password,
                {}
            )
        except OSError as exc:
            raise Exception("Could not reach Odoo. Verify Odoo is running on localhost:8069.") from exc

        if not self.uid:
            raise Exception("Odoo authentication failed. Check database, username, and password.")

    def _execute(self, model, method, args=None, kwargs=None):
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model,
            method,
            args or [],
            kwargs or {},
        )

    def create_customer(self, name, email, phone):
        return self._execute(
            "res.partner",
            "create",
            [[{
                "name": name,
                "email": email,
                "phone": phone,
                "customer_rank": 1,
            }]],
        )

    def get_customers(self, limit=10):
        return self._execute(
            "res.partner",
            "search_read",
            [[["customer_rank", ">", 0]]],
            {
                "fields": ["id", "name", "email", "phone"],
                "limit": limit,
                "order": "id desc",
            },
        )

    def get_sale_orders(self, limit=10):
        return self._execute(
            "sale.order",
            "search_read",
            [[]],
            {"fields": ["name", "partner_id", "state", "amount_total"], "limit": limit, "order": "id desc"},
        )

    def create_sale_order(self, partner_id):
        return self._execute("sale.order", "create", [[{"partner_id": int(partner_id)}]])

    def get_crm_leads(self, limit=10):
        return self._execute(
            "crm.lead",
            "search_read",
            [[]],
            {"fields": ["name", "partner_name", "email_from", "stage_id", "probability"], "limit": limit, "order": "id desc"},
        )

    def create_crm_lead(self, name, email):
        return self._execute("crm.lead", "create", [[{"name": name, "email_from": email}]])

    def get_invoices(self, limit=10):
        return self._execute(
            "account.move",
            "search_read",
            [[["move_type", "=", "out_invoice"]]],
            {"fields": ["name", "partner_id", "state", "invoice_date", "amount_total"], "limit": limit, "order": "id desc"},
        )

    def create_invoice(self, partner_id):
        return self._execute(
            "account.move",
            "create",
            [[{"move_type": "out_invoice", "partner_id": int(partner_id), "invoice_line_ids": []}]],
        )

    def get_journal_entries(self, limit=10):
        return self._execute(
            "account.move",
            "search_read",
            [[["move_type", "=", "entry"]]],
            {"fields": ["name", "date", "state", "journal_id", "ref"], "limit": limit, "order": "id desc"},
        )

    def get_inventory_snapshot(self, limit=10):
        return self._execute(
            "stock.quant",
            "search_read",
            [[["quantity", ">", 0]]],
            {"fields": ["product_id", "location_id", "quantity"], "limit": limit, "order": "id desc"},
        )

    def get_purchase_orders(self, limit=10):
        return self._execute(
            "purchase.order",
            "search_read",
            [[]],
            {"fields": ["name", "partner_id", "state", "amount_total"], "limit": limit, "order": "id desc"},
        )

    def create_purchase_order(self, partner_id):
        return self._execute("purchase.order", "create", [[{"partner_id": int(partner_id)}]])

    def get_manufacturing_orders(self, limit=10):
        return self._execute(
            "mrp.production",
            "search_read",
            [[]],
            {"fields": ["name", "product_id", "product_qty", "state"], "limit": limit, "order": "id desc"},
        )

    def get_products(self, limit=20):
        return self._execute(
            "product.product",
            "search_read",
            [[]],
            {"fields": ["name"], "limit": limit, "order": "id desc"},
        )

    def create_manufacturing_order(self, product_id, quantity):
        product = self._execute(
            "product.product",
            "read",
            [[int(product_id)]],
            {"fields": ["uom_id"], "limit": 1},
        )
        uom_id = product[0]["uom_id"][0] if product and product[0].get("uom_id") else 1
        return self._execute(
            "mrp.production",
            "create",
            [[{"product_id": int(product_id), "product_qty": float(quantity), "product_uom_id": uom_id}]],
        )
