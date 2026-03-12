"""Bot messages and text constants."""
from decimal import Decimal
from typing import List

from src.models.invoice import Invoice, InvoiceItem
from src.validators.thai_validators import format_thai_currency


# Welcome and help messages
WELCOME_MESSAGE = """
👋 Welcome to the Thai E-Tax Invoice Bot!

I'll help you create a tax invoice step by step.

Use /start to begin creating a new invoice.
Use /cancel at any time to cancel the current invoice.
Use /help to see this message again.
"""

HELP_MESSAGE = """
📋 *Thai E-Tax Invoice Bot - Help*

*Commands:*
/start - Start creating a new invoice
/cancel - Cancel current invoice creation
/help - Show this help message

*Invoice Creation Flow:*
1️⃣ Buyer Information (Tax ID, Name, Address, Branch)
2️⃣ Invoice Items (Description, Quantity, Price, Discount)
3️⃣ Additional Notes (optional)
4️⃣ Review and Confirm

*Tips:*
• Seller information is automatically loaded from system settings
• Thai Tax ID must be 13 digits
• Branch code is 5 digits (use 00000 for head office)
• Prices are in Thai Baht (THB)
• You can add multiple items to an invoice
• All data will be validated before submission
"""

START_INVOICE_MESSAGE = """
📝 *Let's create a new tax invoice!*

I'll guide you through each step. You can use /cancel at any time to stop.
"""

# Seller information prompts
SELLER_TAX_ID_PROMPT = """
🏢 *Step {step}/{total}: Seller Tax ID*

Please enter the seller's 13-digit Thai Tax ID.

Example: 1234567890123
"""

SELLER_NAME_PROMPT = """
🏢 *Step {step}/{total}: Seller Name*

Please enter the seller's business name.

Example: ABC Company Limited
"""

SELLER_ADDRESS_PROMPT = """
🏢 *Step {step}/{total}: Seller Address*

Please enter the seller's complete business address.

Example: 123 Main Road, District, Bangkok 10100
"""

SELLER_BRANCH_PROMPT = """
🏢 *Step {step}/{total}: Seller Branch Code*

Please enter the seller's 5-digit branch code.
Use *00000* for head office.

Example: 00000 (head office) or 00001, 00002, etc.
"""

# Buyer information prompts
BUYER_TAX_ID_PROMPT = """
👤 *Step {step}/{total}: Tax ID*

Please enter your 13-digit Tax ID.

Example: 9876543210987
"""

BUYER_NAME_PROMPT = """
👤 *Step {step}/{total}: Your Name*

Please enter your name or business name.

Example: John Doe or XYZ Corporation Limited
"""

BUYER_ADDRESS_PROMPT = """
👤 *Step {step}/{total}: Your Address*

Please enter your address.

Example: 456 Side Street, District, Bangkok
"""

BUYER_POSTAL_CODE_PROMPT = """
👤 *Step {step}/{total}: Postal Code*

Please enter your postal code (5 digits).

Example: 10200
"""

# Item information prompts
ITEM_DESCRIPTION_PROMPT = """
📦 *Step {step}/{total}: Product or Service*

What is the name of the product or service?

Example: Professional Consulting Service
"""

ITEM_QUANTITY_PROMPT = """
📦 *Quantity*

How many?

Example: 1 or 2.5 or 10
"""

ITEM_PRICE_PROMPT = """
💰 *Price per Unit*

Enter the price (in Baht).

Example: 1000 or 1500.50
"""

ITEM_DISCOUNT_PROMPT = """
🏷️ *Discount (Optional)*

Enter discount amount in Baht, or 0 for no discount.

Example: 0 or 100.00
"""

ADD_MORE_ITEMS_PROMPT = """
✅ *Item Added Successfully!*

Item: {description}
Quantity: {quantity}
Unit Price: {price} THB
Discount: {discount} THB
*Line Total: {total} THB*

Would you like to add another item?
"""

# Notes prompt
NOTES_PROMPT = """
📝 *Step {step}/{total}: Additional Notes (Optional)*

Any special notes?

Type your notes or send /skip to continue.
"""

# Confirmation prompt
CONFIRM_PROMPT = """
📋 *Step {step}/{total}: Review Your Invoice*

{invoice_summary}

Everything look good?

Click *Confirm* to generate the invoice or *Cancel* to start over.
"""

# Success and error messages
INVOICE_GENERATED_SUCCESS = """
✅ *Invoice Generated Successfully!*

Your invoice has been created and submitted to the invoice service.

{response_info}

Thank you for using the Thai E-Tax Invoice Bot!
Use /start to create another invoice.
"""

INVOICE_GENERATION_ERROR = """
❌ *Error Generating Invoice*

There was an error generating your invoice:
{error_message}

Please try again with /start or contact support if the problem persists.
"""

CANCEL_MESSAGE = """
❌ *Invoice Cancelled*

Your current invoice has been cancelled.
Use /start to create a new invoice.
"""

# Validation error messages
INVALID_TAX_ID_ERROR = """
❌ *Invalid Tax ID*

{error_message}

Please enter a valid 13-digit Tax ID.
Example: 1234567890123

Attempt {attempt}/{max_attempts}
"""

INVALID_AMOUNT_ERROR = """
❌ *Invalid Amount*

{error_message}

Please enter a valid positive number with maximum 2 decimal places.
Example: 1000 or 1500.50

Attempt {attempt}/{max_attempts}
"""

INVALID_QUANTITY_ERROR = """
❌ *Invalid Quantity*

{error_message}

Please enter a valid positive number.
Example: 1 or 2.5

Attempt {attempt}/{max_attempts}
"""

INVALID_POSTAL_CODE_ERROR = """
❌ *Invalid Postal Code*

{error_message}

Please enter a valid 5-digit postal code.
Example: 10200

Attempt {attempt}/{max_attempts}
"""

MAX_RETRIES_EXCEEDED = """
❌ *Maximum Attempts Exceeded*

You've exceeded the maximum number of attempts for this field.
Your invoice has been cancelled.

Please use /start to begin again.
"""


def format_invoice_summary(invoice: Invoice, items: List[dict]) -> str:
    """Format invoice data for confirmation display.
    
    Args:
        invoice: Invoice object (may have incomplete data)
        items: List of item dictionaries
        
    Returns:
        Formatted invoice summary string
    """
    lines = []
    
    # Seller info
    lines.append("*🏬 From (Seller):*")
    lines.append(f"Tax ID: {invoice.seller.tax_id}")
    lines.append(f"Name: {invoice.seller.name}")
    lines.append(f"Address: {invoice.seller.address}")
    lines.append(f"Postal Code: {invoice.seller.postal_code}")
    lines.append(f"Branch: {invoice.seller.branch_code}")
    lines.append("")
    
    # Buyer info
    lines.append("*👤 To (You):*")
    lines.append(f"Tax ID: {invoice.buyer.tax_id}")
    lines.append(f"Name: {invoice.buyer.name}")
    lines.append(f"Address: {invoice.buyer.address}")
    lines.append(f"Postal Code: {invoice.buyer.postal_code}")
    lines.append("")
    
    # Items
    lines.append("*📦 Items:*")
    for i, item_data in enumerate(items, 1):
        qty = Decimal(str(item_data['quantity']))
        price = Decimal(str(item_data['unit_price']))
        discount = Decimal(str(item_data.get('discount', 0)))
        line_total = (qty * price) - discount
        
        lines.append(f"{i}. {item_data['description']}")
        lines.append(f"   Qty: {qty} × {format_thai_currency(price)} THB")
        if discount > 0:
            lines.append(f"   Discount: {format_thai_currency(discount)} THB")
        lines.append(f"   Subtotal: {format_thai_currency(line_total)} THB")
        lines.append("")
    
    # Totals
    lines.append("*💰 Summary:*")
    lines.append(f"Subtotal: {format_thai_currency(invoice.subtotal)} THB")
    lines.append(f"VAT (7%): {format_thai_currency(invoice.vat_amount)} THB")
    lines.append(f"*Total: {format_thai_currency(invoice.total)} THB*")
    
    if invoice.notes:
        lines.append("")
        lines.append("*📝 Notes:*")
        lines.append(invoice.notes)
    
    return "\n".join(lines)
