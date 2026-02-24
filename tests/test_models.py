"""Unit tests for invoice data models."""
import pytest
from decimal import Decimal
from datetime import datetime

from src.models.invoice import (
    SellerInfo,
    BuyerInfo,
    InvoiceItem,
    Invoice,
    ConversationData
)


class TestSellerInfo:
    """Tests for SellerInfo model."""
    
    def test_valid_seller_info(self):
        """Test creating valid seller info."""
        seller = SellerInfo(
            tax_id="0105536018253",
            name="ABC Company Limited",
            address="123 Main Road, Bangkok",
            branch_code="00000"
        )
        assert seller.tax_id == "0105536018253"
        assert seller.name == "ABC Company Limited"
        assert seller.branch_code == "00000"
    
    def test_invalid_tax_id_length(self):
        """Test seller info with invalid tax ID length."""
        with pytest.raises(Exception):
            SellerInfo(
                tax_id="12345",
                name="ABC Company",
                address="123 Main Road"
            )
    
    def test_default_branch_code(self):
        """Test default branch code."""
        seller = SellerInfo(
            tax_id="0105536018253",
            name="ABC Company",
            address="123 Main Road"
        )
        assert seller.branch_code == "00000"


class TestInvoiceItem:
    """Tests for InvoiceItem model."""
    
    def test_valid_invoice_item(self):
        """Test creating valid invoice item."""
        item = InvoiceItem(
            description="Consulting Service",
            quantity=Decimal("2"),
            unit_price=Decimal("1000.00"),
            discount=Decimal("100.00")
        )
        assert item.description == "Consulting Service"
        assert item.quantity == Decimal("2")
        assert item.line_total == Decimal("1900.00")
    
    def test_line_total_calculation(self):
        """Test line total calculation."""
        item = InvoiceItem(
            description="Product",
            quantity=Decimal("5"),
            unit_price=Decimal("100"),
            discount=Decimal("50")
        )
        assert item.line_total == Decimal("450.00")
    
    def test_zero_discount(self):
        """Test item with zero discount."""
        item = InvoiceItem(
            description="Product",
            quantity=Decimal("1"),
            unit_price=Decimal("500")
        )
        assert item.discount == Decimal("0")
        assert item.line_total == Decimal("500.00")


class TestInvoice:
    """Tests for Invoice model."""
    
    def test_valid_invoice(self):
        """Test creating valid invoice."""
        seller = SellerInfo(
            tax_id="0105536018253",
            name="ABC Company",
            address="123 Main Road"
        )
        buyer = BuyerInfo(
            tax_id="0105536018254",
            name="XYZ Corporation",
            address="456 Side Street"
        )
        items = [
            InvoiceItem(
                description="Item 1",
                quantity=Decimal("2"),
                unit_price=Decimal("100")
            )
        ]
        
        invoice = Invoice(
            seller=seller,
            buyer=buyer,
            items=items
        )
        
        assert invoice.subtotal == Decimal("200.00")
        assert invoice.vat_amount == Decimal("14.00")  # 7% of 200
        assert invoice.total == Decimal("214.00")
    
    def test_multiple_items(self):
        """Test invoice with multiple items."""
        seller = SellerInfo(
            tax_id="0105536018253",
            name="ABC Company",
            address="123 Main Road"
        )
        buyer = BuyerInfo(
            tax_id="0105536018254",
            name="XYZ Corporation",
            address="456 Side Street"
        )
        items = [
            InvoiceItem(
                description="Item 1",
                quantity=Decimal("2"),
                unit_price=Decimal("100")
            ),
            InvoiceItem(
                description="Item 2",
                quantity=Decimal("1"),
                unit_price=Decimal("300"),
                discount=Decimal("50")
            )
        ]
        
        invoice = Invoice(
            seller=seller,
            buyer=buyer,
            items=items
        )
        
        # Subtotal: (2*100) + (1*300-50) = 200 + 250 = 450
        assert invoice.subtotal == Decimal("450.00")
        # VAT: 450 * 0.07 = 31.50
        assert invoice.vat_amount == Decimal("31.50")
        # Total: 450 + 31.50 = 481.50
        assert invoice.total == Decimal("481.50")
    
    def test_to_service_format(self):
        """Test conversion to service format."""
        seller = SellerInfo(
            tax_id="0105536018253",
            name="ABC Company",
            address="123 Main Road"
        )
        buyer = BuyerInfo(
            tax_id="0105536018254",
            name="XYZ Corporation",
            address="456 Side Street"
        )
        items = [
            InvoiceItem(
                description="Item 1",
                quantity=Decimal("1"),
                unit_price=Decimal("100")
            )
        ]
        
        invoice = Invoice(
            seller=seller,
            buyer=buyer,
            items=items
        )
        
        service_format = invoice.to_service_format()
        
        assert "seller" in service_format
        assert "buyer" in service_format
        assert "items" in service_format
        assert service_format["seller"]["taxId"] == "0105536018253"
        assert service_format["total"] == "107.00"
        assert service_format["vatRate"] == "0.07"


class TestConversationData:
    """Tests for ConversationData model."""
    
    def test_create_conversation_data(self):
        """Test creating conversation data."""
        conv = ConversationData(
            user_id=12345,
            username="testuser",
            current_state="START"
        )
        assert conv.user_id == 12345
        assert conv.username == "testuser"
        assert conv.current_state == "START"
        assert conv.items == []
    
    def test_to_invoice(self):
        """Test converting conversation data to invoice."""
        conv = ConversationData(
            user_id=12345,
            current_state="CONFIRM",
            seller_tax_id="0105536018253",
            seller_name="ABC Company",
            seller_address="123 Main Road",
            buyer_tax_id="0105536018254",
            buyer_name="XYZ Corporation",
            buyer_address="456 Side Street",
            items=[
                {
                    "description": "Item 1",
                    "quantity": "1",
                    "unit_price": "100",
                    "discount": "0"
                }
            ]
        )
        
        invoice = conv.to_invoice()
        
        assert invoice.seller.tax_id == "0105536018253"
        assert invoice.buyer.tax_id == "0105536018254"
        assert len(invoice.items) == 1
        assert invoice.items[0].description == "Item 1"
