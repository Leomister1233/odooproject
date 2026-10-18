from django.urls import path

from accounting import views

urlpatterns = [
    path("", views.home_redirect, name="home"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("customers", views.customers, name="customers"),
    path("invoices", views.invoices, name="invoices"),
    path("invoices/create", views.invoice_create, name="invoice_create"),
    path("invoices/<int:invoice_id>", views.invoice_detail, name="invoice_detail"),
    path("payments", views.payments, name="payments"),
    path("vendor-bills", views.vendor_bills, name="vendor_bills"),
    path("journal-entries", views.journal_entries, name="journal_entries"),
    path("reports", views.reports_dashboard, name="reports_dashboard"),
    path("reports/", views.reports_dashboard, name="reports_dashboard_slash"),
    path("reports/aged-receivables/", views.aged_receivables, name="aged_receivables"),
    path("reports/tax-summary/", views.tax_summary, name="tax_summary"),
    path("reports/invoice-status/", views.invoice_status, name="invoice_status"),
    path("reports/customer-balances/", views.customer_balances, name="customer_balances"),
]
