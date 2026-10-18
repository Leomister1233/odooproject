import xmlrpc.client
from datetime import datetime
from decimal import Decimal

from platform_admin.services import get_client_odoo_settings


class OdooServiceBase:
    def __init__(self):
        settings = get_client_odoo_settings()
        self.url = settings["url"]
        self.db = settings["db"]
        self.username = settings["username"]
        self.password = settings["password"]
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

        self.uid = self.common.authenticate(self.db, self.username, self.password, {})
        if not self.uid:
            raise Exception("Odoo authentication failed.")

    def _execute(self, model, method, args=None, kwargs=None):
        try:
            return self.models.execute_kw(
                self.db,
                self.uid,
                self.password,
                model,
                method,
                args or [],
                kwargs or {},
            )
        except OSError as exc:
            raise Exception("The connected Odoo service is temporarily unavailable. Try again shortly.") from exc
        except xmlrpc.client.Fault as exc:
            raise Exception("Odoo could not complete the requested operation. Review the submitted values and try again.") from exc

    def _search_page(self, model, domain, fields, *, limit, offset=0, order="id desc"):
        total = self._execute(model, "search_count", [domain])
        if total and offset >= total:
            offset = ((total - 1) // limit) * limit
        rows = self._execute(model, "search_read", [domain], {
            "fields": fields,
            "limit": limit,
            "offset": max(0, int(offset or 0)),
            "order": order,
        })
        return rows, total

    @staticmethod
    def _decimal(value):
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except Exception:
            return None
