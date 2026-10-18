from django.shortcuts import redirect, render

from odoo_client import OdooClient


def _safe_partner_list(client):
    return client.get_customers(limit=50)


def dashboard(request):
    error = ""
    metrics = {}
    try:
        odoo = OdooClient()
        metrics = {
            "customers": len(odoo.get_customers(limit=200)),
            "sale_orders": len(odoo.get_sale_orders(limit=200)),
            "crm_leads": len(odoo.get_crm_leads(limit=200)),
            "invoices": len(odoo.get_invoices(limit=200)),
            "purchase_orders": len(odoo.get_purchase_orders(limit=200)),
            "manufacturing_orders": len(odoo.get_manufacturing_orders(limit=200)),
        }
    except Exception as exc:
        error = str(exc)
    return render(request, "integration/dashboard.html", {"error": error, "metrics": metrics})


def crm(request):
    message, error = "", ""
    try:
        odoo = OdooClient()
        if request.method == "POST":
            lead_id = odoo.create_crm_lead(request.POST.get("name", "").strip(), request.POST.get("email", "").strip())
            message = f"Lead created. ID: {lead_id}"
        leads = odoo.get_crm_leads(limit=15)
    except Exception as exc:
        leads, error = [], str(exc)
    return render(request, "integration/crm.html", {"leads": leads, "message": message, "error": error})


def customers(request):
    message, error = "", ""
    try:
        odoo = OdooClient()
        if request.method == "POST":
            customer_id = odoo.create_customer(
                name=request.POST.get("name", "").strip(),
                email=request.POST.get("email", "").strip(),
                phone=request.POST.get("phone", "").strip(),
            )
            message = f"Customer created. ID: {customer_id}"
        partners = odoo.get_customers(limit=15)
    except Exception as exc:
        partners, error = [], str(exc)
    return render(request, "integration/customers.html", {"partners": partners, "message": message, "error": error})


def sales(request):
    message, error = "", ""
    try:
        odoo = OdooClient()
        if request.method == "POST":
            sale_id = odoo.create_sale_order(request.POST.get("partner_id"))
            message = f"Sales order created. ID: {sale_id}"
        orders = odoo.get_sale_orders(limit=15)
        partners = _safe_partner_list(odoo)
    except Exception as exc:
        orders, partners, error = [], [], str(exc)
    return render(request, "integration/sales.html", {"orders": orders, "partners": partners, "message": message, "error": error})


def invoicing(request):
    message, error = "", ""
    try:
        odoo = OdooClient()
        if request.method == "POST":
            invoice_id = odoo.create_invoice(request.POST.get("partner_id"))
            message = f"Draft invoice created. ID: {invoice_id}"
        invoices = odoo.get_invoices(limit=15)
        partners = _safe_partner_list(odoo)
    except Exception as exc:
        invoices, partners, error = [], [], str(exc)
    return render(request, "integration/invoicing.html", {"invoices": invoices, "partners": partners, "message": message, "error": error})


def accounting(request):
    error = ""
    try:
        odoo = OdooClient()
        entries = odoo.get_journal_entries(limit=20)
    except Exception as exc:
        entries, error = [], str(exc)
    return render(request, "integration/accounting.html", {"entries": entries, "error": error})


def inventory(request):
    error = ""
    try:
        odoo = OdooClient()
        quants = odoo.get_inventory_snapshot(limit=20)
    except Exception as exc:
        quants, error = [], str(exc)
    return render(request, "integration/inventory.html", {"quants": quants, "error": error})


def purchasing(request):
    message, error = "", ""
    try:
        odoo = OdooClient()
        if request.method == "POST":
            po_id = odoo.create_purchase_order(request.POST.get("partner_id"))
            message = f"RFQ created. ID: {po_id}"
        orders = odoo.get_purchase_orders(limit=15)
        partners = _safe_partner_list(odoo)
    except Exception as exc:
        orders, partners, error = [], [], str(exc)
    return render(request, "integration/purchasing.html", {"orders": orders, "partners": partners, "message": message, "error": error})


def manufacturing(request):
    message, error = "", ""
    try:
        odoo = OdooClient()
        if request.method == "POST":
            mo_id = odoo.create_manufacturing_order(
                request.POST.get("product_id"),
                request.POST.get("quantity", "1"),
            )
            message = f"Manufacturing order created. ID: {mo_id}"
        orders = odoo.get_manufacturing_orders(limit=15)
        products = odoo.get_products(limit=50)
    except Exception as exc:
        orders, products, error = [], [], str(exc)
    return render(request, "integration/manufacturing.html", {"orders": orders, "products": products, "message": message, "error": error})


def home(request):
    return redirect("dashboard")
