from django.contrib import messages as django_messages
from django.shortcuts import redirect, render

from core.pagination import TABLE_FETCH_LIMIT, get_page_window, paginate_items, paginate_remote
from core.table_filters import contains_text, matches_date_range, matches_exact, matches_many2one, normalize_text
from inventory.services import OdooInventoryService


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


def _operation_page(request, operation_code, title, eyebrow, copy):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    rows = []
    state = request.GET.get("state", "").strip()
    partner_id = request.GET.get("partner_id", "").strip()
    origin = request.GET.get("origin", "").strip()
    reference = request.GET.get("reference", "").strip()
    scheduled_from = request.GET.get("scheduled_from", "").strip()
    scheduled_to = request.GET.get("scheduled_to", "").strip()
    transfers_pagination = paginate_items(request, [], f"{operation_code}_transfers")
    partners_pagination = paginate_items(request, [], f"{operation_code}_partners")
    try:
        service = OdooInventoryService()
        window = get_page_window(request, f"{operation_code}_transfers")
        rows, total = service.get_transfers_page(
            state=state or None,
            operation_code=operation_code,
            partner_id=partner_id or None,
            origin=origin or None,
            reference=reference or None,
            scheduled_from=scheduled_from or None,
            scheduled_to=scheduled_to or None,
            limit=window["page_size"],
            offset=window["offset"],
        )
        picking_types = service.get_picking_types(operation_code=operation_code, limit=50)
        partners = service.get_transfer_partners(operation_code=operation_code, limit=200)
        partner_counts = {}
        origin_count = 0
        for row in rows:
            partner = row.get("partner_id")
            if partner:
                partner_name = partner[1]
                partner_counts[partner_name] = partner_counts.get(partner_name, 0) + 1
            if row.get("origin"):
                origin_count += 1
        partner_rows = [{"name": name, "count": count} for name, count in sorted(partner_counts.items(), key=lambda item: (-item[1], item[0]))]
        transfers_pagination = paginate_remote(request, rows, total, f"{operation_code}_transfers")
        partners_pagination = paginate_items(request, partner_rows, f"{operation_code}_partners")
        summary = {
            "total": service.count_transfers(operation_code=operation_code),
            "draft": service.count_transfers(state="draft", operation_code=operation_code),
            "ready": service.count_transfers(state="assigned", operation_code=operation_code),
            "done": service.count_transfers(state="done", operation_code=operation_code),
            "types": picking_types,
            "partner_document_count": len([row for row in rows if row.get("partner_id")]),
            "source_document_count": origin_count,
        }
    except Exception as exc:
        error = str(exc)
        partners = []
        summary = {
            "total": 0,
            "draft": 0,
            "ready": 0,
            "done": 0,
            "types": [],
            "partner_document_count": 0,
            "source_document_count": 0,
        }
        partners = []

    return render(
        request,
        "inventory/operation_workspace.html",
        {
            "transfers": transfers_pagination["items"],
            "transfers_pagination": transfers_pagination,
            "summary": summary,
            "partner_options": partners,
            "partner_rows": partners_pagination["items"],
            "partners_pagination": partners_pagination,
            "error": error,
            "filters": {
                "state": state,
                "partner_id": partner_id,
                "origin": origin,
                "reference": reference,
                "scheduled_from": scheduled_from,
                "scheduled_to": scheduled_to,
            },
            "operation_code": operation_code,
            "page_title": title,
            "page_eyebrow": eyebrow,
            "page_copy": copy,
        },
    )


def dashboard(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    summary = {}
    recent_reference = request.GET.get("recent_reference", "").strip()
    recent_state = request.GET.get("recent_state", "").strip()
    low_stock_query = request.GET.get("low_stock_query", "").strip()
    replenishment_query = request.GET.get("replenishment_query", "").strip()
    try:
        service = OdooInventoryService()
        summary = service.dashboard_summary()
        if recent_reference or recent_state:
            summary["recent_transfers"] = [
                row for row in summary.get("recent_transfers", [])
                if contains_text(row.get("name"), recent_reference)
                and matches_exact(row.get("state"), recent_state)
            ]
        if low_stock_query:
            summary["low_stock_products"] = [
                row for row in summary.get("low_stock_products", [])
                if contains_text(row.get("name"), low_stock_query)
                or contains_text(row.get("default_code"), low_stock_query)
                or contains_text(row.get("categ_id"), low_stock_query)
            ]
        if replenishment_query:
            summary["replenishment_rules"] = [
                row for row in summary.get("replenishment_rules", [])
                if contains_text(row.get("product_id"), replenishment_query)
                or contains_text(row.get("warehouse_id"), replenishment_query)
                or contains_text(row.get("location_id"), replenishment_query)
            ]
        recent_transfers_pagination = paginate_items(request, summary.get("recent_transfers", []), "inventory_recent_transfers")
        low_stock_pagination = paginate_items(request, summary.get("low_stock_products", []), "inventory_low_stock")
        replenishment_pagination = paginate_items(request, summary.get("replenishment_rules", []), "inventory_replenishment_watch")
        summary["recent_transfers"] = recent_transfers_pagination["items"]
        summary["low_stock_products"] = low_stock_pagination["items"]
        summary["replenishment_rules"] = replenishment_pagination["items"]
    except Exception as exc:
        error = str(exc)
        recent_transfers_pagination = paginate_items(request, [], "inventory_recent_transfers")
        low_stock_pagination = paginate_items(request, [], "inventory_low_stock")
        replenishment_pagination = paginate_items(request, [], "inventory_replenishment_watch")

    return render(
        request,
        "inventory/dashboard.html",
        {
            "summary": summary,
            "recent_transfers_pagination": recent_transfers_pagination,
            "low_stock_pagination": low_stock_pagination,
            "replenishment_watch_pagination": replenishment_pagination,
            "error": error,
            "filters": {
                "recent_reference": recent_reference,
                "recent_state": recent_state,
                "low_stock_query": low_stock_query,
                "replenishment_query": replenishment_query,
            },
        },
    )


def products(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    rows = []
    search = request.GET.get("q", "").strip()
    sku_query = request.GET.get("sku", "").strip()
    category_query = request.GET.get("category", "").strip()
    try:
        service = OdooInventoryService()
        window = get_page_window(request, "inventory_products")
        rows, total = service.get_products_page(
            search=search or None,
            sku=sku_query or None,
            category_id=category_query or None,
            limit=window["page_size"],
            offset=window["offset"],
        )
        categories = _collect_many2one_options(service.get_products(limit=200), "categ_id")
        products_pagination = paginate_remote(request, rows, total, "inventory_products")
    except Exception as exc:
        error = str(exc)
        categories = []
        products_pagination = paginate_items(request, [], "inventory_products")

    return render(
        request,
        "inventory/products.html",
        {
            "products": rows,
            "products_pagination": products_pagination,
            "categories": categories,
            "error": error,
            "filters": {"q": search, "sku": sku_query, "category": category_query},
        },
    )


def stock_on_hand(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    rows = []
    products = []
    locations = []
    product_id = request.GET.get("product_id", "").strip()
    location_id = request.GET.get("location_id", "").strip()
    minimum_available = request.GET.get("minimum_available", "").strip()
    try:
        service = OdooInventoryService()
        window = get_page_window(request, "inventory_stock")
        rows, total = service.get_quants_page(
            product_id=product_id or None,
            location_id=location_id or None,
            minimum_available=minimum_available or None,
            limit=window["page_size"],
            offset=window["offset"],
        )
        products = service.get_products(limit=200)
        locations = service.get_locations(limit=200)
        stock_pagination = paginate_remote(request, rows, total, "inventory_stock")
    except Exception as exc:
        error = str(exc)
        stock_pagination = paginate_items(request, [], "inventory_stock")

    return render(
        request,
        "inventory/stock.html",
        {
            "rows": rows,
            "rows_pagination": stock_pagination,
            "products": products,
            "locations": locations,
            "error": error,
            "filters": {"product_id": product_id, "location_id": location_id, "minimum_available": minimum_available},
        },
    )


def transfers(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    rows = []
    state = request.GET.get("state", "").strip()
    operation = request.GET.get("operation", "").strip()
    reference = request.GET.get("reference", "").strip()
    origin = request.GET.get("origin", "").strip()
    scheduled_from = request.GET.get("scheduled_from", "").strip()
    scheduled_to = request.GET.get("scheduled_to", "").strip()
    try:
        service = OdooInventoryService()
        window = get_page_window(request, "inventory_transfers")
        rows, total = service.get_transfers_page(
            state=state or None,
            operation_code=operation or None,
            origin=origin or None,
            reference=reference or None,
            scheduled_from=scheduled_from or None,
            scheduled_to=scheduled_to or None,
            limit=window["page_size"],
            offset=window["offset"],
        )
        transfers_pagination = paginate_remote(request, rows, total, "inventory_transfers")
    except Exception as exc:
        error = str(exc)
        transfers_pagination = paginate_items(request, [], "inventory_transfers")

    return render(
        request,
        "inventory/transfers.html",
        {
            "transfers": rows,
            "transfers_pagination": transfers_pagination,
            "error": error,
            "filters": {
                "state": state,
                "operation": operation,
                "reference": reference,
                "origin": origin,
                "scheduled_from": scheduled_from,
                "scheduled_to": scheduled_to,
            },
        },
    )


def receipts(request):
    return _operation_page(
        request,
        operation_code="incoming",
        title="Receipts",
        eyebrow="Inventory / Receipts",
        copy="Track inbound warehouse receipts and receiving documents from Odoo stock operations.",
    )


def deliveries(request):
    return _operation_page(
        request,
        operation_code="outgoing",
        title="Deliveries",
        eyebrow="Inventory / Deliveries",
        copy="Track outbound delivery orders, fulfillment workload, and completed shipments.",
    )


def internal_operations(request):
    return _operation_page(
        request,
        operation_code="internal",
        title="Internal transfers",
        eyebrow="Inventory / Internal transfers",
        copy="Manage internal stock movements between warehouse locations and operational zones.",
    )


def transfer_create(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    message = ""
    picking_types = []
    locations = []
    products = []
    default_operation = request.GET.get("operation", "").strip()
    try:
        service = OdooInventoryService()
        picking_types = service.get_picking_types(operation_code=default_operation or None, limit=50)
        locations = service.get_locations(limit=200)
        products = service.get_products(limit=200)
        if request.method == "POST":
            line_items = []
            product_ids = request.POST.getlist("product_id")
            quantities = request.POST.getlist("quantity")
            max_len = max(len(product_ids), len(quantities))
            for idx in range(max_len):
                product_id = (product_ids[idx] if idx < len(product_ids) else "").strip()
                quantity = (quantities[idx] if idx < len(quantities) else "").strip()
                if product_id and quantity:
                    line_items.append({"product_id": product_id, "quantity": quantity})

            transfer_id = service.create_transfer(
                picking_type_id=request.POST.get("picking_type_id", "").strip(),
                source_location_id=request.POST.get("source_location_id", "").strip(),
                destination_location_id=request.POST.get("destination_location_id", "").strip(),
                scheduled_date=request.POST.get("scheduled_date", "").strip(),
                origin=request.POST.get("origin", "").strip(),
                line_items=line_items,
            )
            django_messages.success(request, f"Transfer created: {transfer_id}")
            return redirect("inventory_transfer_detail", transfer_id=transfer_id)
    except Exception as exc:
        error = str(exc)

    return render(
        request,
        "inventory/transfer_form.html",
        {
            "picking_types": picking_types,
            "locations": locations,
            "products": products,
            "message": message,
            "error": error,
            "default_operation": default_operation,
        },
    )


def transfer_detail(request, transfer_id):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    message = ""
    transfer = None
    lines_pagination = paginate_items(request, [], "transfer_lines")
    line_product_query = request.GET.get("line_product", "").strip()
    line_description_query = request.GET.get("line_description", "").strip()
    line_state_query = request.GET.get("line_state", "").strip()
    try:
        service = OdooInventoryService()
        if request.method == "POST":
            action = request.POST.get("action", "").strip()
            if action == "confirm":
                service.confirm_transfer(transfer_id)
                message = "Transfer confirmed."
            elif action == "reserve":
                service.reserve_transfer(transfer_id)
                message = "Inventory reserved."
            elif action == "validate":
                service.validate_transfer(transfer_id)
                message = "Transfer validated."
            elif action == "cancel":
                service.cancel_transfer(transfer_id)
                message = "Transfer cancelled."
            if message:
                django_messages.success(request, message)
                return redirect("inventory_transfer_detail", transfer_id=transfer_id)
        transfer = service.get_transfer_detail(transfer_id)
        if transfer:
            lines = transfer.get("lines", [])
            lines = [
                line for line in lines
                if contains_text(line.get("product_id"), line_product_query)
                and contains_text(line.get("name"), line_description_query)
                and matches_exact(line.get("state"), line_state_query)
            ]
            lines_pagination = paginate_items(request, lines, "transfer_lines")
            transfer["lines"] = lines_pagination["items"]
    except Exception as exc:
        error = str(exc)

    return render(
        request,
        "inventory/transfer_detail.html",
        {
            "transfer": transfer,
            "transfer_lines_pagination": lines_pagination,
            "message": message,
            "error": error,
            "filters": {"line_product": line_product_query, "line_description": line_description_query, "line_state": line_state_query},
        },
    )


def locations(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    rows = []
    usage = request.GET.get("usage", "").strip()
    location_query = request.GET.get("location", "").strip()
    try:
        service = OdooInventoryService()
        rows = service.get_location_summary()
        rows = [
            row for row in rows
            if matches_exact(row.get("usage"), usage)
            and (contains_text(row.get("complete_name"), location_query) or contains_text(row.get("name"), location_query))
        ]
        locations_pagination = paginate_items(request, rows, "inventory_locations")
        rows = locations_pagination["items"]
    except Exception as exc:
        error = str(exc)
        locations_pagination = paginate_items(request, [], "inventory_locations")

    return render(
        request,
        "inventory/locations.html",
        {
            "rows": rows,
            "rows_pagination": locations_pagination,
            "error": error,
            "filters": {"usage": usage, "location": location_query},
        },
    )


def adjustments(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    message = ""
    rows = []
    products = []
    locations = []
    product_id = request.GET.get("product_id", "").strip()
    location_id = request.GET.get("location_id", "").strip()
    inventory_date_from = request.GET.get("inventory_date_from", "").strip()
    outdated_only = request.GET.get("outdated_only", "").strip()
    try:
        service = OdooInventoryService()
        if request.method == "POST":
            service.apply_inventory_adjustment(
                quant_id=request.POST.get("quant_id", "").strip(),
                counted_quantity=request.POST.get("counted_quantity", "").strip(),
            )
            django_messages.success(request, "Inventory adjustment applied.")
            return redirect("inventory_adjustments")
        rows = service.get_adjustment_quants(product_id=product_id or None, location_id=location_id or None, limit=TABLE_FETCH_LIMIT)
        products = service.get_products(limit=200)
        locations = service.get_locations(limit=200)
        rows = [
            row for row in rows
            if matches_date_range(row.get("inventory_date"), inventory_date_from or None, None)
            and (outdated_only != "on" or row.get("is_outdated"))
        ]
        adjustments_pagination = paginate_items(request, rows, "inventory_adjustments")
        rows = adjustments_pagination["items"]
    except Exception as exc:
        error = str(exc)
        adjustments_pagination = paginate_items(request, [], "inventory_adjustments")

    return render(
        request,
        "inventory/adjustments.html",
        {
            "rows": rows,
            "rows_pagination": adjustments_pagination,
            "products": products,
            "locations": locations,
            "message": message,
            "error": error,
            "filters": {
                "product_id": product_id,
                "location_id": location_id,
                "inventory_date_from": inventory_date_from,
                "outdated_only": outdated_only,
            },
        },
    )


def replenishment(request):
    protected = _protected(request)
    if protected:
        return protected

    error = ""
    message = ""
    rows = []
    products = []
    locations = []
    location_id = request.GET.get("location_id", "").strip()
    trigger = request.GET.get("trigger", "").strip()
    product_query = request.GET.get("product", "").strip()
    warehouse_query = request.GET.get("warehouse", "").strip()
    try:
        service = OdooInventoryService()
        company_id = service.get_current_company_id()
        if request.method == "POST":
            action = request.POST.get("action", "").strip()
            if action == "create":
                rule_id = service.create_reordering_rule(
                    product_id=request.POST.get("product_id", "").strip(),
                    location_id=request.POST.get("location_id", "").strip(),
                    min_qty=request.POST.get("product_min_qty", "").strip(),
                    max_qty=request.POST.get("product_max_qty", "").strip(),
                    trigger=request.POST.get("trigger", "").strip() or "auto",
                )
                message = f"Reordering rule created: {rule_id}"
            elif action == "update":
                service.update_reordering_rule(
                    rule_id=request.POST.get("rule_id", "").strip(),
                    min_qty=request.POST.get("product_min_qty", "").strip(),
                    max_qty=request.POST.get("product_max_qty", "").strip(),
                    trigger=request.POST.get("trigger", "").strip() or "auto",
                )
                message = "Reordering rule updated."
            elif action == "delete":
                service.delete_reordering_rule(request.POST.get("rule_id", "").strip())
                message = "Reordering rule deleted."
            elif action == "replenish":
                service.trigger_replenishment(request.POST.get("rule_id", "").strip())
                message = "Replenishment action sent to Odoo."

            if message:
                django_messages.success(request, message)
                return redirect("inventory_replenishment")

        rows = service.get_reordering_rules(location_id=location_id or None, trigger=trigger or None, limit=TABLE_FETCH_LIMIT, company_id=company_id)
        products = service.get_products(limit=200)
        locations = service.get_locations(usage="internal", limit=200, company_id=company_id)
        rows = [
            row for row in rows
            if contains_text(row.get("product_id"), product_query)
            and contains_text(row.get("warehouse_id"), warehouse_query)
        ]
        rules_pagination = paginate_items(request, rows, "inventory_replenishment")
        rows = rules_pagination["items"]
    except Exception as exc:
        error = str(exc)
        rules_pagination = paginate_items(request, [], "inventory_replenishment")

    return render(
        request,
        "inventory/replenishment.html",
        {
            "rows": rows,
            "rows_pagination": rules_pagination,
            "products": products,
            "locations": locations,
            "message": message,
            "error": error,
            "filters": {
                "location_id": location_id,
                "trigger": trigger,
                "product": product_query,
                "warehouse": warehouse_query,
            },
        },
    )
