"""Data models for Thai tax invoices using Pydantic."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, computed_field


class SellerInfo(BaseModel):
    """Seller/Issuer information."""
    tax_id: str = Field(..., min_length=13, max_length=13, description="13-digit Thai Tax ID")
    name: str = Field(..., min_length=1, max_length=500, description="Business name")
    address: str = Field(..., min_length=1, max_length=1000, description="Business address")
    branch_code: str = Field(default="00000", description="Branch code (00000 for head office)")
    postal_code: str = Field(default="10000", description="5-digit postal code")
    
    @field_validator('tax_id')
    @classmethod
    def validate_tax_id(cls, v: str) -> str:
        """Ensure tax ID contains only digits."""
        if not v.isdigit():
            raise ValueError("Tax ID must contain only digits")
        return v


class BuyerInfo(BaseModel):
    """Buyer/Recipient information."""
    tax_id: str = Field(..., min_length=13, max_length=13, description="13-digit Thai Tax ID")
    name: str = Field(..., min_length=1, max_length=500, description="Business name")
    address: str = Field(..., min_length=1, max_length=1000, description="Business address")
    branch_code: str = Field(default="00000", description="Branch code (00000 for head office)")
    postal_code: str = Field(default="10000", description="5-digit postal code")
    
    @field_validator('tax_id')
    @classmethod
    def validate_tax_id(cls, v: str) -> str:
        """Ensure tax ID contains only digits."""
        if not v.isdigit():
            raise ValueError("Tax ID must contain only digits")
        return v


class InvoiceItem(BaseModel):
    """Individual line item in an invoice."""
    description: str = Field(..., min_length=1, max_length=1000, description="Item description")
    quantity: Decimal = Field(..., gt=0, description="Item quantity")
    unit_price: Decimal = Field(..., gt=0, description="Price per unit in THB")
    discount: Decimal = Field(default=Decimal("0"), ge=0, description="Discount amount in THB")
    
    @computed_field
    @property
    def line_total(self) -> Decimal:
        """Calculate line total: (quantity * unit_price) - discount."""
        return (self.quantity * self.unit_price) - self.discount
    
    @field_validator('quantity', 'unit_price', 'discount')
    @classmethod
    def round_to_two_decimals(cls, v: Decimal) -> Decimal:
        """Round to 2 decimal places for currency."""
        return v.quantize(Decimal('0.01'))


class Invoice(BaseModel):
    """Complete Thai tax invoice."""
    invoice_number: Optional[str] = Field(default=None, description="Invoice number (auto-generated)")
    issue_date: datetime = Field(default_factory=datetime.now, description="Invoice issue date")
    
    seller: SellerInfo
    buyer: BuyerInfo
    items: List[InvoiceItem] = Field(..., min_length=1, description="Invoice line items")
    
    notes: Optional[str] = Field(default=None, max_length=2000, description="Additional notes")
    
    @computed_field
    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal of all items."""
        return sum(item.line_total for item in self.items)
    
    @computed_field
    @property
    def vat_amount(self) -> Decimal:
        """Calculate VAT amount at 7%."""
        vat_rate = Decimal("0.07")
        return (self.subtotal * vat_rate).quantize(Decimal('0.01'))
    
    @computed_field
    @property
    def total(self) -> Decimal:
        """Calculate total amount including VAT."""
        return self.subtotal + self.vat_amount
    
    def to_service_format(self) -> dict:
        """Convert invoice to InvoiceDto format for signing service /documents/create endpoint.
        
        Matches the structure expected by com.nexus.etax.dto.InvoiceDto
        """
        # Format date as YYYY-MM-DD for LocalDate
        issue_date_str = self.issue_date.strftime("%Y-%m-%d")
        
        return {
            "documentType": "388",  # TaxInvoice type code
            "documentNumber": self.invoice_number or f"INV-{int(self.issue_date.timestamp())}",
            "issueDate": issue_date_str,
            "seller": {
                "name": self.seller.name,
                "taxId": self.seller.tax_id,
                "branchCode": self.seller.branch_code,
                "address": {
                    "lineOne": self.seller.address,
                    "postcodeCode": self.seller.postal_code,
                    "countryId": "TH"
                }
            },
            "buyer": {
                "name": self.buyer.name,
                "taxId": self.buyer.tax_id,
                "branchCode": self.buyer.branch_code,
                "address": {
                    "lineOne": self.buyer.address,
                    "postcodeCode": self.buyer.postal_code,
                    "countryId": "TH"
                }
            },
            "lineItems": [
                {
                    "lineId": str(idx + 1),
                    "name": item.description,
                    "description": item.description,
                    "quantity": float(item.quantity),
                    "unitCode": "C62",  # Unit (UNECE code)
                    "unitPrice": float(item.unit_price),
                    "discountAmount": float(item.discount),
                    "vatRate": 7.00
                }
                for idx, item in enumerate(self.items)
            ],
            "currencyCode": "THB",
            "vatRate": 7.00,
            "noteContent": self.notes
        }


class ConversationData(BaseModel):
    """Conversation state data stored in Redis."""
    user_id: int
    username: Optional[str] = None
    current_state: str
    
    # Partial invoice data
    seller_tax_id: Optional[str] = None
    seller_name: Optional[str] = None
    seller_address: Optional[str] = None
    seller_branch: str = "00000"
    seller_postal_code: str = "10000"
    
    buyer_tax_id: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_branch: str = "00000"
    buyer_postal_code: str = "10000"
    
    items: List[dict] = Field(default_factory=list)
    current_item: dict = Field(default_factory=dict)
    
    notes: Optional[str] = None
    retry_count: int = 0
    
    def to_invoice(self) -> Invoice:
        """Convert conversation data to Invoice model."""
        return Invoice(
            seller=SellerInfo(
                tax_id=self.seller_tax_id,
                name=self.seller_name,
                address=self.seller_address,
                branch_code=self.seller_branch,
                postal_code=self.seller_postal_code
            ),
            buyer=BuyerInfo(
                tax_id=self.buyer_tax_id,
                name=self.buyer_name,
                address=self.buyer_address,
                branch_code=self.buyer_branch,
                postal_code=self.buyer_postal_code
            ),
            items=[InvoiceItem(**item) for item in self.items],
            notes=self.notes
        )
