"""Validators for Thai tax invoice data."""
from decimal import Decimal, InvalidOperation
from typing import Tuple


def validate_thai_tax_id(tax_id: str) -> Tuple[bool, str]:
    """Validate Thai Tax ID with checksum algorithm.
    
    Thai Tax ID is 13 digits with the last digit being a checksum.
    Algorithm: Sum of (digit[i] * (14 - i)) for i=0 to 11, then (11 - (sum % 11)) % 10
    
    Args:
        tax_id: 13-digit tax identification number
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check length
    if len(tax_id) != 13:
        return False, "Tax ID must be exactly 13 digits"
    
    # Check if all digits
    if not tax_id.isdigit():
        return False, "Tax ID must contain only digits"
    
    # Calculate checksum
    try:
        sum_value = 0
        for i in range(12):
            sum_value += int(tax_id[i]) * (13 - i)
        
        checksum = (11 - (sum_value % 11)) % 10
        
        if checksum != int(tax_id[12]):
            return False, "Invalid Tax ID checksum"
        
        return True, ""
    except (ValueError, IndexError) as e:
        return False, f"Invalid Tax ID format: {e}"


def validate_amount(value: str) -> Tuple[bool, str, Decimal]:
    """Validate monetary amount.
    
    Args:
        value: String representation of amount
        
    Returns:
        Tuple of (is_valid, error_message, decimal_value)
    """
    try:
        decimal_value = Decimal(value)
        
        if decimal_value <= 0:
            return False, "Amount must be greater than zero", Decimal("0")
        
        # Check decimal places (max 2 for THB)
        if decimal_value.as_tuple().exponent < -2:
            return False, "Amount can have maximum 2 decimal places", Decimal("0")
        
        # Round to 2 decimal places
        rounded = decimal_value.quantize(Decimal('0.01'))
        
        return True, "", rounded
    except InvalidOperation:
        return False, "Invalid number format", Decimal("0")


def validate_quantity(value: str) -> Tuple[bool, str, Decimal]:
    """Validate item quantity.
    
    Args:
        value: String representation of quantity
        
    Returns:
        Tuple of (is_valid, error_message, decimal_value)
    """
    try:
        decimal_value = Decimal(value)
        
        if decimal_value <= 0:
            return False, "Quantity must be greater than zero", Decimal("0")
        
        # Check decimal places (max 3 for quantity)
        if decimal_value.as_tuple().exponent < -3:
            return False, "Quantity can have maximum 3 decimal places", Decimal("0")
        
        return True, "", decimal_value
    except InvalidOperation:
        return False, "Invalid number format", Decimal("0")


def validate_discount(value: str, max_discount: Decimal) -> Tuple[bool, str, Decimal]:
    """Validate discount amount.
    
    Args:
        value: String representation of discount
        max_discount: Maximum allowed discount (typically line subtotal)
        
    Returns:
        Tuple of (is_valid, error_message, decimal_value)
    """
    try:
        decimal_value = Decimal(value)
        
        if decimal_value < 0:
            return False, "Discount cannot be negative", Decimal("0")
        
        if decimal_value > max_discount:
            return False, f"Discount cannot exceed {max_discount} THB", Decimal("0")
        
        # Check decimal places (max 2 for THB)
        if decimal_value.as_tuple().exponent < -2:
            return False, "Discount can have maximum 2 decimal places", Decimal("0")
        
        # Round to 2 decimal places
        rounded = decimal_value.quantize(Decimal('0.01'))
        
        return True, "", rounded
    except InvalidOperation:
        return False, "Invalid number format", Decimal("0")


def validate_branch_code(branch_code: str) -> Tuple[bool, str]:
    """Validate branch code.
    
    Branch code is typically 5 digits, with "00000" representing head office.
    
    Args:
        branch_code: Branch identification code
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(branch_code) != 5:
        return False, "Branch code must be exactly 5 digits"
    
    if not branch_code.isdigit():
        return False, "Branch code must contain only digits"
    
    return True, ""


def validate_postal_code(postal_code: str) -> Tuple[bool, str]:
    """Validate Thai postal code.
    
    Thai postal code is 5 digits.
    
    Args:
        postal_code: Postal/ZIP code
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(postal_code) != 5:
        return False, "Postal code must be exactly 5 digits"
    
    if not postal_code.isdigit():
        return False, "Postal code must contain only digits"
    
    return True, ""


def format_thai_currency(amount: Decimal) -> str:
    """Format amount as Thai currency with thousand separators.
    
    Args:
        amount: Decimal amount
        
    Returns:
        Formatted string (e.g., "1,234.56")
    """
    return f"{amount:,.2f}"
