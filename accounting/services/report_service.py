from datetime import date
from decimal import Decimal


class ReportServiceMixin:
    def get_monthly_revenue(self, months=6):
        posted = self.get_posted_customer_invoices(limit=1000)
        months_map = {}
        for inv in posted:
            inv_date = self._parse_date(inv.get("invoice_date"))
            if not inv_date:
                continue
            key = inv_date.strftime("%Y-%m")
            months_map[key] = months_map.get(key, Decimal("0")) + self._decimal(inv.get("amount_total"))
        month_keys = sorted(months_map.keys())[-months:]
        return [{"month": key, "amount": float(months_map[key])} for key in month_keys]

    def get_report_dashboard(self):
        today = date.today()
        invoices = self.get_customer_invoices(limit=1500)
        posted = [inv for inv in invoices if inv.get("state") == "posted"]
        paid = [inv for inv in invoices if inv.get("payment_state") == "paid"]
        open_invoices = [inv for inv in posted if inv.get("payment_state") != "paid"]

        overdue = []
        for inv in open_invoices:
            due = self._parse_date(inv.get("invoice_date_due"))
            if due and due < today:
                overdue.append(inv)

        total_revenue = sum((self._decimal(inv.get("amount_total")) for inv in posted), Decimal("0"))
        outstanding = sum((self._decimal(inv.get("amount_residual")) for inv in open_invoices), Decimal("0"))
        tax_collected = sum((self._decimal(inv.get("amount_tax")) for inv in posted), Decimal("0"))
        draft_count = len([inv for inv in invoices if inv.get("state") == "draft"])
        posted_count = len(posted)
        currency = next((inv.get("currency_id") for inv in invoices if inv.get("currency_id")), None)
        monthly_revenue = self.get_monthly_revenue(months=6)

        status_summary = {
            "draft": draft_count,
            "posted": posted_count,
            "paid": len(paid),
            "partial": len([inv for inv in invoices if inv.get("payment_state") == "partial"]),
            "not_paid": len([inv for inv in invoices if inv.get("payment_state") == "not_paid"]),
            "overdue": len(overdue),
        }

        return {
            "kpis": {
                "total_revenue": float(total_revenue),
                "paid_invoices": len(paid),
                "open_invoices": len(open_invoices),
                "overdue_invoices": len(overdue),
                "outstanding_receivables": float(outstanding),
                "tax_collected": float(tax_collected),
                "draft_invoices": draft_count,
                "posted_invoices": posted_count,
            },
            "recent_invoices": self.get_recent_invoices(limit=10),
            "status_summary": status_summary,
            "monthly_revenue": monthly_revenue,
            "currency": currency,
        }

    def get_aged_receivables(self):
        today = date.today()
        invoices = self.get_unpaid_customer_invoices(limit=1500)
        currency = next((inv.get("currency_id") for inv in invoices if inv.get("currency_id")), None)
        buckets = {
            "not_due": {"label": "Not due", "count": 0, "total": Decimal("0"), "rows": []},
            "d1_30": {"label": "1-30 days overdue", "count": 0, "total": Decimal("0"), "rows": []},
            "d31_60": {"label": "31-60 days overdue", "count": 0, "total": Decimal("0"), "rows": []},
            "d61_90": {"label": "61-90 days overdue", "count": 0, "total": Decimal("0"), "rows": []},
            "d90_plus": {"label": "90+ days overdue", "count": 0, "total": Decimal("0"), "rows": []},
        }
        for inv in invoices:
            due = self._parse_date(inv.get("invoice_date_due"))
            residual = self._decimal(inv.get("amount_residual"))
            days_overdue = 0
            key = "not_due"
            if due:
                days_overdue = (today - due).days
                if days_overdue <= 0:
                    key = "not_due"
                elif days_overdue <= 30:
                    key = "d1_30"
                elif days_overdue <= 60:
                    key = "d31_60"
                elif days_overdue <= 90:
                    key = "d61_90"
                else:
                    key = "d90_plus"
            bucket = buckets[key]
            bucket["count"] += 1
            bucket["total"] += residual
            bucket["rows"].append({
                "invoice": inv.get("name"),
                "customer": (inv.get("partner_id") or [None, "-"])[1],
                "due_date": inv.get("invoice_date_due"),
                "days_overdue": max(days_overdue, 0),
                "total_amount": float(self._decimal(inv.get("amount_total"))),
                "amount_due": float(residual),
                "payment_state": inv.get("payment_state"),
                "currency_id": inv.get("currency_id"),
            })
        for bucket in buckets.values():
            bucket["total"] = float(bucket["total"])
        return {"currency": currency, "buckets": buckets}

    def get_tax_summary(self):
        posted = self.get_posted_customer_invoices(limit=1500)
        currency = next((inv.get("currency_id") for inv in posted if inv.get("currency_id")), None)
        untaxed = sum((self._decimal(inv.get("amount_untaxed")) for inv in posted), Decimal("0"))
        tax = sum((self._decimal(inv.get("amount_tax")) for inv in posted), Decimal("0"))
        total = sum((self._decimal(inv.get("amount_total")) for inv in posted), Decimal("0"))
        rate = Decimal("0")
        if untaxed > 0:
            rate = (tax / untaxed) * Decimal("100")
        monthly_tax = {}
        for inv in posted:
            inv_date = self._parse_date(inv.get("invoice_date"))
            if not inv_date:
                continue
            key = inv_date.strftime("%Y-%m")
            monthly_tax[key] = monthly_tax.get(key, Decimal("0")) + self._decimal(inv.get("amount_tax"))
        last6 = sorted(monthly_tax.keys())[-6:]
        return {
            "total_untaxed": float(untaxed),
            "total_tax": float(tax),
            "total_amount": float(total),
            "tax_rate_approx": float(rate),
            "monthly_tax": [{"month": key, "amount": float(monthly_tax[key])} for key in last6],
            "currency": currency,
        }

    def get_invoice_status_report(self):
        today = date.today()
        invoices = self.get_customer_invoices(limit=1500)
        currency = next((inv.get("currency_id") for inv in invoices if inv.get("currency_id")), None)
        groups = {
            "draft": {"count": 0, "amount_total": Decimal("0"), "residual_total": Decimal("0"), "rows": []},
            "posted": {"count": 0, "amount_total": Decimal("0"), "residual_total": Decimal("0"), "rows": []},
            "paid": {"count": 0, "amount_total": Decimal("0"), "residual_total": Decimal("0"), "rows": []},
            "partial": {"count": 0, "amount_total": Decimal("0"), "residual_total": Decimal("0"), "rows": []},
            "not_paid": {"count": 0, "amount_total": Decimal("0"), "residual_total": Decimal("0"), "rows": []},
            "overdue": {"count": 0, "amount_total": Decimal("0"), "residual_total": Decimal("0"), "rows": []},
        }

        for inv in invoices:
            base_keys = []
            if inv.get("state") == "draft":
                base_keys.append("draft")
            if inv.get("state") == "posted":
                base_keys.append("posted")
            if inv.get("payment_state") in {"paid", "partial", "not_paid"}:
                base_keys.append(inv.get("payment_state"))
            due = self._parse_date(inv.get("invoice_date_due"))
            if inv.get("state") == "posted" and inv.get("payment_state") != "paid" and due and due < today:
                base_keys.append("overdue")
            row = inv
            for key in set(base_keys):
                groups[key]["count"] += 1
                groups[key]["amount_total"] += self._decimal(inv.get("amount_total"))
                groups[key]["residual_total"] += self._decimal(inv.get("amount_residual"))
                groups[key]["rows"].append(row)
        for key in groups:
            groups[key]["amount_total"] = float(groups[key]["amount_total"])
            groups[key]["residual_total"] = float(groups[key]["residual_total"])
        return {"currency": currency, "groups": groups}

    def get_customer_balance_report(self):
        posted = self.get_posted_customer_invoices(limit=2000)
        currency = next((inv.get("currency_id") for inv in posted if inv.get("currency_id")), None)
        per_customer = {}
        for inv in posted:
            partner = inv.get("partner_id") or [0, "Unknown"]
            partner_id, partner_name = partner[0], partner[1]
            if partner_id not in per_customer:
                per_customer[partner_id] = {
                    "customer": partner_name,
                    "invoice_count": 0,
                    "total_invoiced": Decimal("0"),
                    "outstanding_balance": Decimal("0"),
                }
            item = per_customer[partner_id]
            item["invoice_count"] += 1
            item["total_invoiced"] += self._decimal(inv.get("amount_total"))
            item["outstanding_balance"] += self._decimal(inv.get("amount_residual"))
        rows = []
        for data in per_customer.values():
            total_paid = data["total_invoiced"] - data["outstanding_balance"]
            rows.append({
                "customer": data["customer"],
                "invoice_count": data["invoice_count"],
                "total_invoiced": float(data["total_invoiced"]),
                "total_paid": float(total_paid),
                "outstanding_balance": float(data["outstanding_balance"]),
            })
        rows.sort(key=lambda x: x["outstanding_balance"], reverse=True)
        return {"currency": currency, "rows": rows}

    def dashboard_metrics(self):
        invoices = self.get_invoices(limit=200)
        revenue = sum(inv.get("amount_total", 0.0) for inv in invoices if inv.get("state") == "posted")
        unpaid = sum(inv.get("amount_residual", 0.0) for inv in invoices if inv.get("payment_state") in {"not_paid", "partial"})
        overdue = [inv for inv in invoices if inv.get("payment_state") == "not_paid" and inv.get("invoice_date_due")]
        return {
            "total_revenue": revenue,
            "unpaid_total": unpaid,
            "overdue_count": len(overdue),
            "invoice_count": len(invoices),
        }
