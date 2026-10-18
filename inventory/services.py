from collections import defaultdict
from datetime import date
from decimal import Decimal
import xmlrpc.client

from accounting.services.base import OdooServiceBase


class OdooInventoryService(OdooServiceBase):
    def __init__(self):
        super().__init__()
        self._current_company_id = None
        self._ensure_inventory_available()

    def _ensure_inventory_available(self):
        module = self._execute(
            "ir.module.module",
            "search_read",
            [[["name", "=", "stock"], ["state", "=", "installed"]]],
            {"fields": ["id"], "limit": 1},
        )
        if not module:
            raise Exception("Odoo Inventory (`stock`) is not installed in this database. Install the Inventory module in Odoo before using this workspace.")

    @staticmethod
    def _normalize_id(value):
        if isinstance(value, (list, tuple)):
            if not value:
                raise Exception("Odoo did not return a valid record identifier.")
            return int(value[0])
        return int(value)

    def _execute_allowing_none_fault(self, model, method, args=None, kwargs=None):
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
            if "cannot marshal None unless allow_none is enabled" in exc.faultString:
                return True
            raise Exception("Odoo could not complete the requested inventory operation. Review the submitted values and try again.") from exc

    def get_current_company_id(self):
        if self._current_company_id is None:
            user = self._execute("res.users", "read", [[self.uid]], {"fields": ["company_id"]})
            self._current_company_id = (user[0].get("company_id") or [None])[0]
        return self._current_company_id

    def get_products(self, search=None, limit=100):
        domain = [["active", "=", True], ["type", "in", ["product", "consu"]]]
        if search:
            domain.append(["name", "ilike", search])
        return self._execute(
            "product.product",
            "search_read",
            [domain],
            {
                "fields": ["id", "name", "default_code", "qty_available", "virtual_available", "uom_id", "categ_id"],
                "limit": limit,
                "order": "id desc",
            },
        )

    def get_products_page(self, search=None, sku=None, category_id=None, limit=50, offset=0):
        domain = [["active", "=", True], ["type", "in", ["product", "consu"]]]
        if search:
            domain.append(["name", "ilike", search])
        if sku:
            domain.append(["default_code", "ilike", sku])
        if category_id:
            try:
                domain.append(["categ_id", "=", int(category_id)])
            except (TypeError, ValueError):
                pass
        return self._search_page(
            "product.product", domain,
            ["id", "name", "default_code", "qty_available", "virtual_available", "uom_id", "categ_id"],
            limit=limit, offset=offset, order="id desc",
        )

    def get_locations(self, usage=None, limit=200, company_id=None):
        domain = [["active", "=", True]]
        if usage:
            domain.append(["usage", "=", usage])
        if company_id:
            domain.append(["company_id", "=", int(company_id)])
        return self._execute(
            "stock.location",
            "search_read",
            [domain],
            {
                "fields": ["id", "name", "complete_name", "usage"],
                "limit": limit,
                "order": "complete_name asc",
            },
        )

    def get_warehouses(self, limit=50, company_id=None):
        domain = []
        if company_id:
            domain.append(["company_id", "=", int(company_id)])
        return self._execute(
            "stock.warehouse",
            "search_read",
            [domain],
            {
                "fields": ["id", "name", "company_id"],
                "limit": limit,
                "order": "id asc",
            },
        )

    def get_picking_types(self, operation_code=None, limit=50):
        domain = []
        if operation_code:
            domain.append(["code", "=", operation_code])
        return self._execute(
            "stock.picking.type",
            "search_read",
            [domain],
            {
                "fields": ["id", "name", "code", "warehouse_id", "default_location_src_id", "default_location_dest_id"],
                "limit": limit,
                "order": "sequence asc, id asc",
            },
        )

    def get_quants(self, product_id=None, location_id=None, limit=200):
        domain = [["quantity", "!=", 0]]
        if product_id:
            domain.append(["product_id", "=", int(product_id)])
        if location_id:
            domain.append(["location_id", "=", int(location_id)])
        rows = self._execute(
            "stock.quant",
            "search_read",
            [domain],
            {
                "fields": ["id", "product_id", "location_id", "quantity", "reserved_quantity"],
                "limit": limit,
                "order": "id desc",
            },
        )
        for row in rows:
            quantity = Decimal(str(row.get("quantity") or 0))
            reserved = Decimal(str(row.get("reserved_quantity") or 0))
            row["available_quantity"] = float(quantity - reserved)
        return rows

    def get_quants_page(self, product_id=None, location_id=None, minimum_available=None, limit=50, offset=0):
        domain = [["quantity", "!=", 0]]
        if product_id:
            domain.append(["product_id", "=", int(product_id)])
        if location_id:
            domain.append(["location_id", "=", int(location_id)])
        if minimum_available not in (None, ""):
            try:
                domain.append(["available_quantity", ">=", float(minimum_available)])
            except (TypeError, ValueError):
                pass
        rows, total = self._search_page(
            "stock.quant", domain,
            ["id", "product_id", "location_id", "quantity", "reserved_quantity"],
            limit=limit, offset=offset, order="id desc",
        )
        for row in rows:
            quantity = Decimal(str(row.get("quantity") or 0))
            reserved = Decimal(str(row.get("reserved_quantity") or 0))
            row["available_quantity"] = float(quantity - reserved)
        return rows, total

    def get_adjustment_quants(self, product_id=None, location_id=None, limit=200):
        domain = [["product_id", "!=", False], ["location_id", "!=", False]]
        if product_id:
            domain.append(["product_id", "=", int(product_id)])
        if location_id:
            domain.append(["location_id", "=", int(location_id)])
        rows = self._execute(
            "stock.quant",
            "search_read",
            [domain],
            {
                "fields": [
                    "id",
                    "product_id",
                    "location_id",
                    "quantity",
                    "reserved_quantity",
                    "inventory_quantity",
                    "inventory_diff_quantity",
                    "inventory_date",
                    "is_outdated",
                ],
                "limit": limit,
                "order": "id desc",
            },
        )
        for row in rows:
            quantity = Decimal(str(row.get("quantity") or 0))
            reserved = Decimal(str(row.get("reserved_quantity") or 0))
            counted = row.get("inventory_quantity")
            row["available_quantity"] = float(quantity - reserved)
            row["counted_quantity"] = float(counted if counted is not None else quantity)
        return rows

    def apply_inventory_adjustment(self, quant_id, counted_quantity):
        quant_id = self._normalize_id(quant_id)
        counted_quantity = float(counted_quantity)
        self._execute(
            "stock.quant",
            "write",
            [[quant_id], {"inventory_quantity": counted_quantity, "inventory_date": date.today().isoformat()}],
        )
        return self._execute_allowing_none_fault("stock.quant", "action_apply_inventory", [[quant_id]])

    def get_transfers(self, state=None, operation_code=None, partner_id=None, origin=None, limit=100):
        domain = []
        if state:
            domain.append(["state", "=", state])
        if operation_code:
            domain.append(["picking_type_code", "=", operation_code])
        if partner_id:
            domain.append(["partner_id", "=", int(partner_id)])
        if origin:
            domain.append(["origin", "ilike", origin])
        return self._execute(
            "stock.picking",
            "search_read",
            [domain],
            {
                "fields": [
                    "id",
                    "name",
                    "origin",
                    "partner_id",
                    "state",
                    "scheduled_date",
                    "date_done",
                    "picking_type_id",
                    "picking_type_code",
                    "location_id",
                    "location_dest_id",
                    "group_id",
                ],
                "limit": limit,
                "order": "scheduled_date desc, id desc",
            },
        )

    def get_transfers_page(self, state=None, operation_code=None, partner_id=None, origin=None,
                           reference=None, scheduled_from=None, scheduled_to=None, limit=50, offset=0):
        domain = []
        if state:
            domain.append(["state", "=", state])
        if operation_code:
            domain.append(["picking_type_code", "=", operation_code])
        if partner_id:
            domain.append(["partner_id", "=", int(partner_id)])
        if origin:
            domain.append(["origin", "ilike", origin])
        if reference:
            domain.append(["name", "ilike", reference])
        if scheduled_from:
            domain.append(["scheduled_date", ">=", scheduled_from])
        if scheduled_to:
            domain.append(["scheduled_date", "<=", f"{scheduled_to} 23:59:59"])
        return self._search_page(
            "stock.picking", domain,
            ["id", "name", "origin", "partner_id", "state", "scheduled_date", "date_done", "picking_type_id", "picking_type_code", "location_id", "location_dest_id", "group_id"],
            limit=limit, offset=offset, order="scheduled_date desc, id desc",
        )

    def count_transfers(self, state=None, operation_code=None):
        domain = []
        if state:
            domain.append(["state", "=", state])
        if operation_code:
            domain.append(["picking_type_code", "=", operation_code])
        return self._execute("stock.picking", "search_count", [domain])

    def get_transfer_partners(self, operation_code=None, limit=100):
        domain = [["partner_id", "!=", False]]
        if operation_code:
            domain.append(["picking_type_code", "=", operation_code])
        rows = self._execute(
            "stock.picking",
            "search_read",
            [domain],
            {
                "fields": ["partner_id"],
                "limit": limit,
                "order": "id desc",
            },
        )
        unique_partners = []
        seen_ids = set()
        for row in rows:
            partner = row.get("partner_id")
            if not partner:
                continue
            partner_id = int(partner[0])
            if partner_id in seen_ids:
                continue
            seen_ids.add(partner_id)
            unique_partners.append({"id": partner_id, "name": partner[1]})
        return unique_partners

    def get_transfer_detail(self, transfer_id):
        transfer_id = self._normalize_id(transfer_id)
        rows = self._execute(
            "stock.picking",
            "read",
            [[transfer_id]],
            {
                "fields": [
                    "id",
                    "name",
                    "origin",
                    "partner_id",
                    "state",
                    "scheduled_date",
                    "date_done",
                    "picking_type_id",
                    "picking_type_code",
                    "location_id",
                    "location_dest_id",
                    "move_ids_without_package",
                    "move_ids",
                ],
            },
        )
        if not rows:
            return None
        transfer = rows[0]
        move_ids = transfer.get("move_ids_without_package") or transfer.get("move_ids") or []
        lines = []
        if move_ids:
            lines = self._execute(
                "stock.move",
                "read",
                [move_ids],
                {
                    "fields": [
                        "id",
                        "name",
                        "product_id",
                        "product_uom_qty",
                        "quantity",
                        "product_uom",
                        "location_id",
                        "location_dest_id",
                        "state",
                    ],
                },
            )
        transfer["lines"] = lines
        return transfer

    def create_transfer(self, picking_type_id, source_location_id, destination_location_id, scheduled_date, origin, line_items):
        if not line_items:
            raise Exception("At least one transfer line is required.")

        picking_type = self._execute(
            "stock.picking.type",
            "read",
            [[int(picking_type_id)]],
            {"fields": ["default_location_src_id", "default_location_dest_id"]},
        )
        source_id = int(source_location_id) if source_location_id else (picking_type[0].get("default_location_src_id") or [None])[0]
        destination_id = int(destination_location_id) if destination_location_id else (picking_type[0].get("default_location_dest_id") or [None])[0]

        if not source_id or not destination_id:
            raise Exception("Source and destination locations are required for inventory transfers.")

        move_lines = []
        for item in line_items:
            product = self._execute(
                "product.product",
                "read",
                [[int(item["product_id"])]],
                {"fields": ["name", "uom_id"]},
            )[0]
            move_lines.append(
                [
                    0,
                    0,
                    {
                        "name": product.get("name"),
                        "product_id": int(item["product_id"]),
                        "product_uom_qty": float(item["quantity"]),
                        "product_uom": (product.get("uom_id") or [None])[0],
                        "location_id": source_id,
                        "location_dest_id": destination_id,
                    },
                ]
            )

        formatted_scheduled_date = scheduled_date.replace("T", " ").strip() if scheduled_date else False
        if formatted_scheduled_date and len(formatted_scheduled_date) == 16:
            formatted_scheduled_date = f"{formatted_scheduled_date}:00"

        transfer_id = self._execute(
            "stock.picking",
            "create",
            [[
                {
                    "picking_type_id": int(picking_type_id),
                    "location_id": source_id,
                    "location_dest_id": destination_id,
                    "scheduled_date": formatted_scheduled_date,
                    "origin": origin or False,
                    "move_ids_without_package": move_lines,
                }
            ]],
        )
        transfer_id = self._normalize_id(transfer_id)
        self.confirm_transfer(transfer_id)
        return transfer_id

    def confirm_transfer(self, transfer_id):
        transfer_id = self._normalize_id(transfer_id)
        return self._execute("stock.picking", "action_confirm", [[transfer_id]])

    def reserve_transfer(self, transfer_id):
        transfer_id = self._normalize_id(transfer_id)
        return self._execute("stock.picking", "action_assign", [[transfer_id]])

    def validate_transfer(self, transfer_id):
        transfer_id = self._normalize_id(transfer_id)
        transfer = self.get_transfer_detail(transfer_id)
        if not transfer:
            raise Exception("Transfer not found.")

        for line in transfer.get("lines", []):
            planned_qty = float(line.get("product_uom_qty") or 0)
            done_qty = float(line.get("quantity") or 0)
            if planned_qty > 0 and done_qty <= 0 and line.get("state") not in {"done", "cancel"}:
                self._execute("stock.move", "write", [[int(line["id"])], {"quantity": planned_qty}])

        result = self._execute("stock.picking", "button_validate", [[transfer_id]])
        if isinstance(result, dict):
            wizard_model = result.get("res_model")
            wizard_id = result.get("res_id")
            context = result.get("context") or {}
            if wizard_model == "stock.immediate.transfer":
                return self._execute(wizard_model, "process", [[int(wizard_id)]], {"context": context})
            if wizard_model == "stock.backorder.confirmation":
                return self._execute(wizard_model, "process", [[int(wizard_id)]], {"context": context})
        return result

    def cancel_transfer(self, transfer_id):
        transfer_id = self._normalize_id(transfer_id)
        return self._execute("stock.picking", "action_cancel", [[transfer_id]])

    def get_reordering_rules(self, location_id=None, trigger=None, limit=200, company_id=None):
        domain = []
        if location_id:
            domain.append(["location_id", "=", int(location_id)])
        if trigger:
            domain.append(["trigger", "=", trigger])
        if company_id:
            domain.append(["company_id", "=", int(company_id)])
        return self._execute(
            "stock.warehouse.orderpoint",
            "search_read",
            [domain],
            {
                "fields": [
                    "id",
                    "product_id",
                    "location_id",
                    "warehouse_id",
                    "company_id",
                    "product_min_qty",
                    "product_max_qty",
                    "qty_to_order",
                    "qty_forecast",
                    "trigger",
                ],
                "limit": limit,
                "order": "id desc",
            },
        )

    def create_reordering_rule(self, product_id, location_id, warehouse_id=None, min_qty=0, max_qty=0, trigger="auto"):
        location = self._execute(
            "stock.location",
            "read",
            [[int(location_id)]],
            {"fields": ["company_id", "warehouse_id", "usage"]},
        )
        location_company_id = (location[0].get("company_id") or [None])[0]
        location_warehouse_id = (location[0].get("warehouse_id") or [None])[0]
        warehouse_id = location_warehouse_id or (int(warehouse_id) if warehouse_id else None)
        company_id = location_company_id
        current_company_id = self.get_current_company_id()

        if not warehouse_id:
            raise Exception("The selected location is not linked to a warehouse in Odoo.")
        if not company_id:
            warehouse = self._execute(
                "stock.warehouse",
                "read",
                [[int(warehouse_id)]],
                {"fields": ["company_id"]},
            )
            company_id = (warehouse[0].get("company_id") or [None])[0]
        if not company_id:
            raise Exception("The selected location or warehouse does not expose a company in Odoo.")
        if current_company_id and int(company_id) != int(current_company_id):
            raise Exception("The selected location belongs to a different company than the active Odoo company.")

        rule_id = self._execute(
            "stock.warehouse.orderpoint",
            "create",
            [[
                {
                    "product_id": int(product_id),
                    "location_id": int(location_id),
                    "warehouse_id": int(warehouse_id),
                    "company_id": int(company_id),
                    "product_min_qty": float(min_qty),
                    "product_max_qty": float(max_qty),
                    "trigger": trigger or "auto",
                }
            ]],
        )
        return self._normalize_id(rule_id)

    def update_reordering_rule(self, rule_id, min_qty, max_qty, trigger):
        rule_id = self._normalize_id(rule_id)
        return self._execute(
            "stock.warehouse.orderpoint",
            "write",
            [[rule_id], {"product_min_qty": float(min_qty), "product_max_qty": float(max_qty), "trigger": trigger or "auto"}],
        )

    def delete_reordering_rule(self, rule_id):
        rule_id = self._normalize_id(rule_id)
        return self._execute("stock.warehouse.orderpoint", "unlink", [[rule_id]])

    def trigger_replenishment(self, rule_id):
        rule_id = self._normalize_id(rule_id)
        return self._execute("stock.warehouse.orderpoint", "action_replenish", [[rule_id]])

    def dashboard_summary(self):
        products = self.get_products(limit=500)
        quants = self.get_quants(limit=500)
        locations = self.get_locations(limit=200)
        transfers = self.get_transfers(limit=200)
        rules = self.get_reordering_rules(limit=500, company_id=self.get_current_company_id())

        on_hand = sum(Decimal(str(row.get("quantity") or 0)) for row in quants)
        reserved = sum(Decimal(str(row.get("reserved_quantity") or 0)) for row in quants)
        open_transfers = [row for row in transfers if row.get("state") not in {"done", "cancel"}]
        low_stock = [row for row in products if float(row.get("qty_available") or 0) <= 0]
        rules_to_replenish = [row for row in rules if float(row.get("qty_to_order") or 0) > 0]

        operation_counts = defaultdict(int)
        for row in open_transfers:
            operation_counts[row.get("picking_type_code") or "other"] += 1

        return {
            "product_count": len(products),
            "location_count": len(locations),
            "on_hand_quantity": float(on_hand),
            "reserved_quantity": float(reserved),
            "open_transfer_count": len(open_transfers),
            "incoming_open": operation_counts.get("incoming", 0),
            "outgoing_open": operation_counts.get("outgoing", 0),
            "internal_open": operation_counts.get("internal", 0),
            "reordering_rule_count": len(rules),
            "replenishment_alert_count": len(rules_to_replenish),
            "recent_transfers": transfers,
            "low_stock_products": low_stock,
            "replenishment_rules": rules_to_replenish,
        }

    def get_location_summary(self):
        locations = self.get_locations(limit=500)
        quants = self.get_quants(limit=2000)
        per_location = defaultdict(lambda: {"quantity": Decimal("0"), "reserved": Decimal("0"), "lines": 0})
        for row in quants:
            location = row.get("location_id") or [0, "-"]
            location_id = location[0]
            per_location[location_id]["quantity"] += Decimal(str(row.get("quantity") or 0))
            per_location[location_id]["reserved"] += Decimal(str(row.get("reserved_quantity") or 0))
            per_location[location_id]["lines"] += 1

        rows = []
        for location in locations:
            totals = per_location.get(location["id"], {"quantity": Decimal("0"), "reserved": Decimal("0"), "lines": 0})
            rows.append(
                {
                    **location,
                    "quantity": float(totals["quantity"]),
                    "reserved_quantity": float(totals["reserved"]),
                    "available_quantity": float(totals["quantity"] - totals["reserved"]),
                    "line_count": totals["lines"],
                }
            )
        return rows
