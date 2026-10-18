from datetime import datetime

from django.contrib import messages as django_messages
from django.utils.timezone import localdate

from django.shortcuts import redirect, render

from accounting.services.odoo_accounting import OdooAccountingService
from core.pagination import TABLE_FETCH_LIMIT, get_page_window, paginate_items, paginate_named_groups, paginate_remote
from core.table_filters import contains_text, matches_date_range, matches_exact, matches_many2one, normalize_text


def _is_auth(request):
    return bool(request.session.get("portal_authenticated"))


def _protected(request):
    if not _is_auth(request):
        return redirect("login")
    return None


def _collect_many2one_options(rows, field):
    options = []
    seen_ids = set()
    for row in rows:
        value = row.get(field)
        if not isinstance(value, (list, tuple)) or not value:
            continue
        key = str(value[0])
        if key in seen_ids:
            continue
        seen_ids.add(key)
        options.append({"id": value[0], "name": value[1] if len(value) > 1 else value[0]})
    options.sort(key=lambda item: normalize_text(item.get("name")).lower())
    return options


def _collect_distinct_values(rows, field):
    values = []
    seen = set()
    for row in rows:
        value = str(row.get(field) or "")
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
    values.sort()
    return values


def home_redirect(request):
    if _is_auth(request):
        return redirect("dashboard")
    return redirect("login")


def dashboard(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    metrics = {}
    invoices = []
    statuses = {"draft": 0, "posted": 0, "paid": 0, "overdue": 0}
    currency = None
    customer_query = request.GET.get("customer", "").strip()
    status_query = request.GET.get("status", "").strip()

    try:
        service = OdooAccountingService()
        metrics = service.dashboard_metrics()
        invoices = service.get_invoices(limit=TABLE_FETCH_LIMIT)
        currency = next((inv.get("currency_id") for inv in invoices if inv.get("currency_id")), None)
        for inv in invoices:
            state = inv.get("state")
            payment_state = inv.get("payment_state")
            if state == "draft":
                statuses["draft"] += 1
            elif payment_state == "paid":
                statuses["paid"] += 1
            elif payment_state in {"not_paid", "partial"} and inv.get("invoice_date_due") and str(inv.get("invoice_date_due")) < str(datetime.utcnow().date()):
                statuses["overdue"] += 1
            else:
                statuses["posted"] += 1
        if customer_query:
            invoices = [inv for inv in invoices if contains_text(inv.get("partner_id"), customer_query)]
        if status_query:
            invoices = [
                inv for inv in invoices
                if contains_text(inv.get("state"), status_query) or contains_text(inv.get("payment_state"), status_query)
            ]
        recent_invoices_pagination = paginate_items(request, invoices, "dashboard_invoices")
        invoices = recent_invoices_pagination["items"]
    except Exception as exc:
        error = str(exc)
        recent_invoices_pagination = paginate_items(request, [], "dashboard_invoices")

    return render(request, "accounting/dashboard.html", {
        "error": error,
        "metrics": metrics,
        "recent_invoices": invoices,
        "recent_invoices_pagination": recent_invoices_pagination,
        "statuses": statuses,
        "currency": currency,
        "filters": {"customer": customer_query, "status": status_query},
    })


def customers(request):
    protected = _protected(request)
    if protected:
        return protected

    message, error = "", ""
    partners = []
    name_query = request.GET.get("name", "").strip()
    email_query = request.GET.get("email", "").strip()
    phone_query = request.GET.get("phone", "").strip()
    try:
        service = OdooAccountingService()
        if request.method == "POST":
            customer_id = service.create_customer(
                request.POST.get("name", "").strip(),
                request.POST.get("email", "").strip(),
                request.POST.get("phone", "").strip(),
            )
            django_messages.success(request, f"Customer created: {customer_id}")
            return redirect("customers")
        window = get_page_window(request, "customers")
        partners, total = service.get_customers_page(
            name=name_query or None,
            email=email_query or None,
            phone=phone_query or None,
            limit=window["page_size"],
            offset=window["offset"],
        )
        partners_pagination = paginate_remote(request, partners, total, "customers")
    except Exception as exc:
        error = str(exc)
        partners_pagination = paginate_items(request, [], "customers")

    return render(
        request,
        "accounting/customers.html",
        {
            "partners": partners,
            "partners_pagination": partners_pagination,
            "message": message,
            "error": error,
            "filters": {"name": name_query, "email": email_query, "phone": phone_query},
        },
    )


def invoices(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    status = request.GET.get("status", "").strip()
    partner_id = request.GET.get("partner_id", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    reference = request.GET.get("reference", "").strip()
    journal_id = request.GET.get("journal_id", "").strip()
    payment_state = request.GET.get("payment_state", "").strip()
    try:
        service = OdooAccountingService()

        state_filter = ""
        if status in {"draft", "posted"}:
            state_filter = status

        window = get_page_window(request, "invoices")
        invoice_rows, invoice_total = service.get_invoices_page(
            state=state_filter or None,
            partner_id=partner_id or None,
            date_from=date_from or None,
            date_to=date_to or None,
            reference=reference or None,
            journal_id=journal_id or None,
            payment_state=payment_state or None,
            limit=window["page_size"],
            offset=window["offset"],
        )
        partners = service.get_customers(limit=200)
        journals = service.get_sales_journals()
        payment_states = ["not_paid", "in_payment", "paid", "partial", "reversed"]
        invoices_pagination = paginate_remote(request, invoice_rows, invoice_total, "invoices")
    except Exception as exc:
        invoice_rows, partners, journals, payment_states, error = [], [], [], [], str(exc)
        invoices_pagination = paginate_items(request, [], "invoices")

    return render(request, "accounting/invoice_list.html", {
        "invoices": invoice_rows,
        "invoices_pagination": invoices_pagination,
        "partners": partners,
        "journals": journals,
        "payment_states": payment_states,
        "error": error,
        "filters": {
            "status": status,
            "partner_id": partner_id,
            "date_from": date_from,
            "date_to": date_to,
            "reference": reference,
            "journal_id": journal_id,
            "payment_state": payment_state,
        },
    })


def invoice_create(request):
    protected = _protected(request)
    if protected:
        return protected

    message, error = "", ""
    partners, journals, payment_terms, taxes, products, currencies = [], [], [], [], [], []
    try:
        service = OdooAccountingService()
        partners = service.get_customers(limit=200)
        journals = service.get_sales_journals()
        payment_terms = service.get_payment_terms()
        taxes = service.get_taxes(limit=100)
        products = service.get_products(limit=200)
        currencies = service.get_currencies()
        if request.method == "POST":
            line_items = []
            descriptions = request.POST.getlist("description")
            quantities = request.POST.getlist("quantity")
            unit_prices = request.POST.getlist("unit_price")
            product_ids = request.POST.getlist("product_id")
            tax_ids_list = request.POST.getlist("tax_id")

            max_len = max(len(descriptions), len(quantities), len(unit_prices), len(product_ids), len(tax_ids_list))
            for idx in range(max_len):
                description = (descriptions[idx] if idx < len(descriptions) else "").strip()
                quantity = (quantities[idx] if idx < len(quantities) else "").strip()
                unit_price = (unit_prices[idx] if idx < len(unit_prices) else "").strip()
                product_id = (product_ids[idx] if idx < len(product_ids) else "").strip()
                tax_id = (tax_ids_list[idx] if idx < len(tax_ids_list) else "").strip()
                if description and quantity and unit_price:
                    line_items.append({
                        "description": description,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "product_id": product_id or None,
                        "tax_ids": [tax_id] if tax_id else [],
                    })
            invoice_id = service.create_invoice(
                partner_id=request.POST.get("partner_id"),
                invoice_date=request.POST.get("invoice_date", "").strip(),
                due_date=request.POST.get("due_date", "").strip(),
                reference=request.POST.get("reference", "").strip(),
                journal_id=request.POST.get("journal_id", "").strip(),
                payment_term_id=request.POST.get("payment_term_id", "").strip(),
                line_items=line_items,
            )
            if request.POST.get("post_now") == "on":
                service.post_invoice(invoice_id)
            django_messages.success(request, f"Invoice created: {invoice_id}")
            return redirect("invoice_detail", invoice_id=invoice_id)
    except Exception as exc:
        error = str(exc)

    return render(request, "accounting/invoice_form.html", {
        "partners": partners,
        "journals": journals,
        "payment_terms": payment_terms,
        "taxes": taxes,
        "products": products,
        "currencies": currencies,
        "message": message,
        "error": error,
    })


def invoice_detail(request, invoice_id):
    protected = _protected(request)
    if protected:
        return protected

    message, error = "", ""
    invoice = None
    lines_pagination = paginate_items(request, [], "invoice_lines")
    line_product_query = request.GET.get("line_product", "").strip()
    line_description_query = request.GET.get("line_description", "").strip()
    line_tax_query = request.GET.get("line_tax", "").strip()
    try:
        service = OdooAccountingService()
        if request.method == "POST":
            action = request.POST.get("action")
            if action == "post":
                service.post_invoice(invoice_id)
                django_messages.success(request, "Invoice posted successfully.")
                return redirect("invoice_detail", invoice_id=invoice_id)
            if action == "payment":
                amount = request.POST.get("amount", "0")
                service.register_payment(invoice_id, amount)
                django_messages.success(request, "Payment registered.")
                return redirect("invoice_detail", invoice_id=invoice_id)
        invoice = service.get_invoice_detail(invoice_id)
        if invoice:
            lines = invoice.get("lines", [])
            if line_product_query:
                lines = [line for line in lines if contains_text(line.get("product_id"), line_product_query)]
            if line_description_query:
                lines = [line for line in lines if contains_text(line.get("name"), line_description_query)]
            if line_tax_query:
                lines = [line for line in lines if contains_text(line.get("tax_ids"), line_tax_query)]
            lines_pagination = paginate_items(request, lines, "invoice_lines")
            invoice["lines"] = lines_pagination["items"]
    except Exception as exc:
        error = str(exc)

    return render(
        request,
        "accounting/invoice_detail.html",
        {
            "invoice": invoice,
            "invoice_lines_pagination": lines_pagination,
            "message": message,
            "error": error,
            "filters": {"line_product": line_product_query, "line_description": line_description_query, "line_tax": line_tax_query},
        },
    )


def payments(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    payment_name = request.GET.get("payment_name", "").strip()
    partner_query = request.GET.get("partner", "").strip()
    payment_type = request.GET.get("payment_type", "").strip()
    payment_state = request.GET.get("state", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    try:
        service = OdooAccountingService()
        window = get_page_window(request, "payments")
        payment_rows, total = service.get_payments_page(
            name=payment_name or None, partner=partner_query or None,
            payment_type=payment_type or None, state=payment_state or None,
            date_from=date_from or None, date_to=date_to or None,
            limit=window["page_size"], offset=window["offset"],
        )
        payment_types = ["inbound", "outbound"]
        payment_states = ["draft", "in_process", "paid", "canceled"]
        payments_pagination = paginate_remote(request, payment_rows, total, "payments")
    except Exception as exc:
        payment_rows, error = [], str(exc)
        payment_types, payment_states = [], []
        payments_pagination = paginate_items(request, [], "payments")

    return render(
        request,
        "accounting/payments.html",
        {
            "payments": payment_rows,
            "payments_pagination": payments_pagination,
            "payment_types": payment_types,
            "payment_states": payment_states,
            "error": error,
            "filters": {
                "payment_name": payment_name,
                "partner": partner_query,
                "payment_type": payment_type,
                "state": payment_state,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


def vendor_bills(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    rows = []
    vendor_query = request.GET.get("vendor", "").strip()
    reference = request.GET.get("reference", "").strip()
    state = request.GET.get("state", "").strip()
    payment_state = request.GET.get("payment_state", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    try:
        service = OdooAccountingService()
        window = get_page_window(request, "vendor_bills")
        rows, total = service.get_vendor_bills_page(
            vendor=vendor_query or None, reference=reference or None,
            state=state or None, payment_state=payment_state or None,
            date_from=date_from or None, date_to=date_to or None,
            limit=window["page_size"], offset=window["offset"],
        )
        states = ["draft", "posted", "cancel"]
        payment_states = ["not_paid", "in_payment", "paid", "partial", "reversed"]
        bills_pagination = paginate_remote(request, rows, total, "vendor_bills")
    except Exception as exc:
        error = str(exc)
        states, payment_states = [], []
        bills_pagination = paginate_items(request, [], "vendor_bills")

    return render(
        request,
        "accounting/vendor_bills.html",
        {
            "bills": rows,
            "bills_pagination": bills_pagination,
            "states": states,
            "payment_states": payment_states,
            "error": error,
            "filters": {
                "vendor": vendor_query,
                "reference": reference,
                "state": state,
                "payment_state": payment_state,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


def journal_entries(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    rows = []
    entry_name = request.GET.get("entry_name", "").strip()
    journal_id = request.GET.get("journal_id", "").strip()
    reference = request.GET.get("reference", "").strip()
    state = request.GET.get("state", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    try:
        service = OdooAccountingService()
        window = get_page_window(request, "journal_entries")
        rows, total = service.get_journal_entries_page(
            name=entry_name or None, journal_id=journal_id or None,
            reference=reference or None, state=state or None,
            date_from=date_from or None, date_to=date_to or None,
            limit=window["page_size"], offset=window["offset"],
        )
        journals = _collect_many2one_options(service.get_journal_entries(limit=200), "journal_id")
        states = ["draft", "posted", "cancel"]
        entries_pagination = paginate_remote(request, rows, total, "journal_entries")
    except Exception as exc:
        error = str(exc)
        journals, states = [], []
        entries_pagination = paginate_items(request, [], "journal_entries")

    return render(
        request,
        "accounting/journal_entries.html",
        {
            "entries": rows,
            "entries_pagination": entries_pagination,
            "journals": journals,
            "states": states,
            "error": error,
            "filters": {
                "entry_name": entry_name,
                "journal_id": journal_id,
                "reference": reference,
                "state": state,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


def reports_dashboard(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    data = {}
    customer_query = request.GET.get("customer", "").strip()
    state_query = request.GET.get("state", "").strip()
    payment_query = request.GET.get("payment_state", "").strip()
    try:
        service = OdooAccountingService()
        data = service.get_report_dashboard()
        recent_invoices = service.get_recent_invoices(limit=TABLE_FETCH_LIMIT)
        recent_invoices = [
            inv for inv in recent_invoices
            if contains_text(inv.get("partner_id"), customer_query)
            and matches_exact(inv.get("state"), state_query)
            and matches_exact(inv.get("payment_state"), payment_query)
        ]
        report_states = _collect_distinct_values(recent_invoices, "state")
        report_payment_states = _collect_distinct_values(recent_invoices, "payment_state")
        recent_invoices_pagination = paginate_items(request, recent_invoices, "reports_recent_invoices")
        recent_invoices = recent_invoices_pagination["items"]
    except Exception as exc:
        error = str(exc)
        recent_invoices = []
        report_states, report_payment_states = [], []
        recent_invoices_pagination = paginate_items(request, [], "reports_recent_invoices")

    context = {
        "error": error,
        "kpis": data.get("kpis", {}),
        "recent_invoices": recent_invoices,
        "recent_invoices_pagination": recent_invoices_pagination,
        "report_states": report_states,
        "report_payment_states": report_payment_states,
        "status_summary": data.get("status_summary", {}),
        "monthly_revenue": data.get("monthly_revenue", []),
        "currency": data.get("currency"),
        "filters": {"customer": customer_query, "state": state_query, "payment_state": payment_query},
    }
    return render(request, "accounting/reports.html", context)


def aged_receivables(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    buckets = {}
    currency = None
    invoice_query = request.GET.get("invoice", "").strip()
    customer_query = request.GET.get("customer", "").strip()
    payment_state = request.GET.get("payment_state", "").strip()
    try:
        service = OdooAccountingService()
        data = service.get_aged_receivables()
        raw_buckets = data.get("buckets", {})
        for bucket in raw_buckets.values():
            filtered_rows = [
                row for row in bucket.get("rows", [])
                if contains_text(row.get("invoice"), invoice_query)
                and contains_text(row.get("customer"), customer_query)
                and matches_exact(row.get("payment_state"), payment_state)
            ]
            bucket["rows"] = filtered_rows
            bucket["count"] = len(filtered_rows)
            bucket["total"] = round(sum(float(row.get("amount_due") or 0) for row in filtered_rows), 2)
        buckets = paginate_named_groups(request, raw_buckets, "aged_receivables")
        currency = data.get("currency")
        payment_states = sorted({str(row.get("payment_state") or "") for bucket in raw_buckets.values() for row in bucket.get("rows", []) if row.get("payment_state")})
    except Exception as exc:
        error = str(exc)
        buckets = {}
        payment_states = []
    return render(
        request,
        "accounting/aged_receivables.html",
        {
            "buckets": buckets,
            "currency": currency,
            "error": error,
            "today": localdate(),
            "payment_states": payment_states,
            "filters": {"invoice": invoice_query, "customer": customer_query, "payment_state": payment_state},
        },
    )


def tax_summary(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    summary = {}
    try:
        service = OdooAccountingService()
        summary = service.get_tax_summary()
    except Exception as exc:
        error = str(exc)
    return render(request, "accounting/tax_summary.html", {"summary": summary, "error": error})


def invoice_status(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    groups = {}
    currency = None
    invoice_query = request.GET.get("invoice", "").strip()
    customer_query = request.GET.get("customer", "").strip()
    state_query = request.GET.get("state", "").strip()
    payment_query = request.GET.get("payment_state", "").strip()
    try:
        service = OdooAccountingService()
        data = service.get_invoice_status_report()
        raw_groups = data.get("groups", {})
        for group in raw_groups.values():
            filtered_rows = [
                inv for inv in group.get("rows", [])
                if contains_text(inv.get("name"), invoice_query)
                and contains_text(inv.get("partner_id"), customer_query)
                and matches_exact(inv.get("state"), state_query)
                and matches_exact(inv.get("payment_state"), payment_query)
            ]
            group["rows"] = filtered_rows
            group["count"] = len(filtered_rows)
            group["amount_total"] = round(sum(float(inv.get("amount_total") or 0) for inv in filtered_rows), 2)
            group["residual_total"] = round(sum(float(inv.get("amount_residual") or 0) for inv in filtered_rows), 2)
        groups = paginate_named_groups(request, raw_groups, "invoice_status")
        currency = data.get("currency")
        states = sorted({str(inv.get("state") or "") for group in raw_groups.values() for inv in group.get("rows", []) if inv.get("state")})
        payment_states = sorted({str(inv.get("payment_state") or "") for group in raw_groups.values() for inv in group.get("rows", []) if inv.get("payment_state")})
    except Exception as exc:
        error = str(exc)
        groups = {}
        states, payment_states = [], []
    return render(
        request,
        "accounting/invoice_status.html",
        {
            "groups": groups,
            "currency": currency,
            "error": error,
            "states": states,
            "payment_states": payment_states,
            "filters": {"invoice": invoice_query, "customer": customer_query, "state": state_query, "payment_state": payment_query},
        },
    )


def customer_balances(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    rows = []
    currency = None
    customer_query = request.GET.get("customer", "").strip()
    minimum_outstanding = request.GET.get("minimum_outstanding", "").strip()
    try:
        service = OdooAccountingService()
        data = service.get_customer_balance_report()
        rows = data.get("rows", [])
        currency = data.get("currency")
        if customer_query:
            rows = [row for row in rows if contains_text(row.get("customer"), customer_query)]
        if minimum_outstanding:
            try:
                minimum_value = float(minimum_outstanding)
                rows = [row for row in rows if float(row.get("outstanding_balance") or 0) >= minimum_value]
            except ValueError:
                pass
        balances_pagination = paginate_items(request, rows, "customer_balances")
        rows = balances_pagination["items"]
    except Exception as exc:
        error = str(exc)
        balances_pagination = paginate_items(request, [], "customer_balances")
    return render(
        request,
        "accounting/customer_balances.html",
        {
            "rows": rows,
            "rows_pagination": balances_pagination,
            "currency": currency,
            "error": error,
            "filters": {"customer": customer_query, "minimum_outstanding": minimum_outstanding},
        },
    )


def reports(request):
    return reports_dashboard(request)
