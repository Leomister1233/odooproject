from accounting.services.base import OdooServiceBase
from accounting.services.customer_service import CustomerServiceMixin
from accounting.services.invoice_service import InvoiceServiceMixin
from accounting.services.metadata_service import MetadataServiceMixin
from accounting.services.payment_service import PaymentServiceMixin
from accounting.services.report_service import ReportServiceMixin


class OdooAccountingService(
    OdooServiceBase,
    CustomerServiceMixin,
    InvoiceServiceMixin,
    PaymentServiceMixin,
    MetadataServiceMixin,
    ReportServiceMixin,
):
    """Facade service preserving current import path while delegating to modular mixins."""

    pass
