"""Unit tests for Thai validators."""
import pytest
from decimal import Decimal

from src.validators.thai_validators import (
    validate_thai_tax_id,
    validate_amount,
    validate_quantity,
    validate_discount,
    validate_branch_code,
    format_thai_currency
)


class TestThaiTaxIDValidator:
    """Tests for Thai Tax ID validation."""
    
    def test_valid_tax_id(self):
        """Test valid Thai Tax ID."""
        # Using a valid checksum calculation
        is_valid, error_msg = validate_thai_tax_id("0105536018253")
        assert is_valid is True
        assert error_msg == ""
    
    def test_invalid_length(self):
        """Test tax ID with invalid length."""
        is_valid, error_msg = validate_thai_tax_id("12345")
        assert is_valid is False
        assert "13 digits" in error_msg
    
    def test_non_digit_characters(self):
        """Test tax ID with non-digit characters."""
        is_valid, error_msg = validate_thai_tax_id("12345678901AB")
        assert is_valid is False
        assert "only digits" in error_msg
    
    def test_invalid_checksum(self):
        """Test tax ID with invalid checksum."""
        is_valid, error_msg = validate_thai_tax_id("1234567890120")
        assert is_valid is False
        assert "checksum" in error_msg


class TestAmountValidator:
    """Tests for amount validation."""
    
    def test_valid_amount(self):
        """Test valid amount."""
        is_valid, error_msg, value = validate_amount("100.50")
        assert is_valid is True
        assert error_msg == ""
        assert value == Decimal("100.50")
    
    def test_zero_amount(self):
        """Test zero amount."""
        is_valid, error_msg, value = validate_amount("0")
        assert is_valid is False
        assert "greater than zero" in error_msg
    
    def test_negative_amount(self):
        """Test negative amount."""
        is_valid, error_msg, value = validate_amount("-50")
        assert is_valid is False
        assert "greater than zero" in error_msg
    
    def test_too_many_decimals(self):
        """Test amount with too many decimal places."""
        is_valid, error_msg, value = validate_amount("100.123")
        assert is_valid is False
        assert "2 decimal places" in error_msg
    
    def test_invalid_format(self):
        """Test invalid number format."""
        is_valid, error_msg, value = validate_amount("abc")
        assert is_valid is False
        assert "Invalid number" in error_msg


class TestQuantityValidator:
    """Tests for quantity validation."""
    
    def test_valid_quantity(self):
        """Test valid quantity."""
        is_valid, error_msg, value = validate_quantity("5")
        assert is_valid is True
        assert error_msg == ""
        assert value == Decimal("5")
    
    def test_decimal_quantity(self):
        """Test decimal quantity."""
        is_valid, error_msg, value = validate_quantity("2.5")
        assert is_valid is True
        assert value == Decimal("2.5")
    
    def test_zero_quantity(self):
        """Test zero quantity."""
        is_valid, error_msg, value = validate_quantity("0")
        assert is_valid is False
        assert "greater than zero" in error_msg


class TestDiscountValidator:
    """Tests for discount validation."""
    
    def test_valid_discount(self):
        """Test valid discount."""
        is_valid, error_msg, value = validate_discount("50.00", Decimal("100"))
        assert is_valid is True
        assert error_msg == ""
        assert value == Decimal("50.00")
    
    def test_zero_discount(self):
        """Test zero discount."""
        is_valid, error_msg, value = validate_discount("0", Decimal("100"))
        assert is_valid is True
        assert value == Decimal("0")
    
    def test_negative_discount(self):
        """Test negative discount."""
        is_valid, error_msg, value = validate_discount("-10", Decimal("100"))
        assert is_valid is False
        assert "cannot be negative" in error_msg
    
    def test_exceeds_max_discount(self):
        """Test discount exceeding maximum."""
        is_valid, error_msg, value = validate_discount("150", Decimal("100"))
        assert is_valid is False
        assert "cannot exceed" in error_msg


class TestBranchCodeValidator:
    """Tests for branch code validation."""
    
    def test_valid_branch_code(self):
        """Test valid branch code."""
        is_valid, error_msg = validate_branch_code("00000")
        assert is_valid is True
        assert error_msg == ""
    
    def test_invalid_length(self):
        """Test branch code with invalid length."""
        is_valid, error_msg = validate_branch_code("123")
        assert is_valid is False
        assert "5 digits" in error_msg
    
    def test_non_digit_characters(self):
        """Test branch code with non-digit characters."""
        is_valid, error_msg = validate_branch_code("0000A")
        assert is_valid is False
        assert "only digits" in error_msg


class TestCurrencyFormatter:
    """Tests for currency formatting."""
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert format_thai_currency(Decimal("1000")) == "1,000.00"
        assert format_thai_currency(Decimal("1234.56")) == "1,234.56"
        assert format_thai_currency(Decimal("1000000")) == "1,000,000.00"
