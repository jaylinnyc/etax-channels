"""Services package."""
from .invoice_client import invoice_service, InvoiceServiceClient

__all__ = [
    "invoice_service",
    "InvoiceServiceClient"
]
