from django.urls import path

from inventory import views


urlpatterns = [
    path("inventory", views.dashboard, name="inventory_dashboard"),
    path("inventory/products", views.products, name="inventory_products"),
    path("inventory/stock", views.stock_on_hand, name="inventory_stock"),
    path("inventory/receipts", views.receipts, name="inventory_receipts"),
    path("inventory/deliveries", views.deliveries, name="inventory_deliveries"),
    path("inventory/internal-transfers", views.internal_operations, name="inventory_internal_operations"),
    path("inventory/adjustments", views.adjustments, name="inventory_adjustments"),
    path("inventory/replenishment", views.replenishment, name="inventory_replenishment"),
    path("inventory/transfers", views.transfers, name="inventory_transfers"),
    path("inventory/transfers/create", views.transfer_create, name="inventory_transfer_create"),
    path("inventory/transfers/<int:transfer_id>", views.transfer_detail, name="inventory_transfer_detail"),
    path("inventory/locations", views.locations, name="inventory_locations"),
]
