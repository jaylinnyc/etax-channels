"""Telegram bot conversation handlers."""
from decimal import Decimal
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import structlog

from src.bot.states import ConversationState, get_next_state, get_state_progress
from src.bot import messages
from src.models.invoice import ConversationData, Invoice
from src.database.repository import repository
from src.validators.thai_validators import (
    validate_thai_tax_id,
    validate_amount,
    validate_quantity,
    validate_discount,
    validate_branch_code,
    format_thai_currency
)
from src.services.invoice_client import invoice_service, settings_service
from src.config import settings

logger = structlog.get_logger()


# Command Handlers

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command."""
    user = update.effective_user
    logger.info("start_command", user_id=user.id, username=user.username)
    
    # Fetch company settings from API
    success, settings_data = await settings_service.get_company_settings()
    
    if not success or not settings_data:
        await update.message.reply_text(
            "❌ Unable to fetch company settings from the server. Please try again later or contact support.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Extract company info
    company_info = settings_service.extract_company_info(settings_data)
    
    if not company_info:
        await update.message.reply_text(
            "❌ Company settings are incomplete. Please configure company information in the system settings.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Initialize conversation data with seller info pre-populated
    conversation_data = ConversationData(
        user_id=user.id,
        username=user.username,
        current_state=str(ConversationState.BUYER_TAX_ID),
        seller_tax_id=company_info["tax_id"],
        seller_name=company_info["name"],
        seller_address=company_info["address"],
        seller_branch=company_info["branch_code"],
        seller_postal_code=company_info["postal_code"]
    )
    
    await repository.save_conversation_state(user.id, conversation_data)
    
    await update.message.reply_text(
        messages.START_INVOICE_MESSAGE,
        parse_mode='Markdown'
    )
    
    # Move directly to buyer information (skip seller questions)
    step, total = get_state_progress(ConversationState.BUYER_TAX_ID)
    await update.message.reply_text(
        messages.BUYER_TAX_ID_PROMPT.format(step=step, total=total),
        parse_mode='Markdown'
    )
    
    return ConversationState.BUYER_TAX_ID


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        messages.HELP_MESSAGE,
        parse_mode='Markdown'
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel command."""
    user = update.effective_user
    logger.info("cancel_command", user_id=user.id)
    
    await repository.delete_conversation(user.id)
    await update.message.reply_text(messages.CANCEL_MESSAGE, parse_mode='Markdown')
    
    return ConversationHandler.END


# Seller Information Handlers

async def handle_seller_tax_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle seller tax ID input."""
    user = update.effective_user
    tax_id = update.message.text.strip()
    
    # Validate
    is_valid, error_msg = validate_thai_tax_id(tax_id)
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    if not is_valid:
        conversation.retry_count += 1
        if conversation.retry_count >= settings.max_retry_attempts:
            await repository.delete_conversation(user.id)
            await update.message.reply_text(messages.MAX_RETRIES_EXCEEDED, parse_mode='Markdown')
            return ConversationHandler.END
        
        await repository.save_conversation_state(user.id, conversation)
        await update.message.reply_text(
            messages.INVALID_TAX_ID_ERROR.format(
                error_message=error_msg,
                attempt=conversation.retry_count,
                max_attempts=settings.max_retry_attempts
            ),
            parse_mode='Markdown'
        )
        return ConversationState.SELLER_TAX_ID
    
    # Save and move to next
    conversation.seller_tax_id = tax_id
    conversation.retry_count = 0
    conversation.current_state = str(ConversationState.SELLER_NAME)
    await repository.save_conversation_state(user.id, conversation)
    
    step, total = get_state_progress(ConversationState.SELLER_NAME)
    await update.message.reply_text(
        messages.SELLER_NAME_PROMPT.format(step=step, total=total),
        parse_mode='Markdown'
    )
    
    return ConversationState.SELLER_NAME


async def handle_seller_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle seller name input."""
    user = update.effective_user
    name = update.message.text.strip()
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    conversation.seller_name = name
    conversation.current_state = str(ConversationState.SELLER_ADDRESS)
    await repository.save_conversation_state(user.id, conversation)
    
    step, total = get_state_progress(ConversationState.SELLER_ADDRESS)
    await update.message.reply_text(
        messages.SELLER_ADDRESS_PROMPT.format(step=step, total=total),
        parse_mode='Markdown'
    )
    
    return ConversationState.SELLER_ADDRESS


async def handle_seller_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle seller address input."""
    user = update.effective_user
    address = update.message.text.strip()
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    conversation.seller_address = address
    conversation.current_state = str(ConversationState.SELLER_BRANCH)
    await repository.save_conversation_state(user.id, conversation)
    
    step, total = get_state_progress(ConversationState.SELLER_BRANCH)
    await update.message.reply_text(
        messages.SELLER_BRANCH_PROMPT.format(step=step, total=total),
        parse_mode='Markdown'
    )
    
    return ConversationState.SELLER_BRANCH


async def handle_seller_branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle seller branch code input."""
    user = update.effective_user
    branch_code = update.message.text.strip()
    
    # Validate
    is_valid, error_msg = validate_branch_code(branch_code)
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    if not is_valid:
        conversation.retry_count += 1
        if conversation.retry_count >= settings.max_retry_attempts:
            await repository.delete_conversation(user.id)
            await update.message.reply_text(messages.MAX_RETRIES_EXCEEDED, parse_mode='Markdown')
            return ConversationHandler.END
        
        await repository.save_conversation_state(user.id, conversation)
        await update.message.reply_text(
            messages.INVALID_BRANCH_CODE_ERROR.format(
                error_message=error_msg,
                attempt=conversation.retry_count,
                max_attempts=settings.max_retry_attempts
            ),
            parse_mode='Markdown'
        )
        return ConversationState.SELLER_BRANCH
    
    conversation.seller_branch = branch_code
    conversation.retry_count = 0
    conversation.current_state = str(ConversationState.BUYER_TAX_ID)
    await repository.save_conversation_state(user.id, conversation)
    
    step, total = get_state_progress(ConversationState.BUYER_TAX_ID)
    await update.message.reply_text(
        messages.BUYER_TAX_ID_PROMPT.format(step=step, total=total),
        parse_mode='Markdown'
    )
    
    return ConversationState.BUYER_TAX_ID


# Buyer Information Handlers

async def handle_buyer_tax_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle buyer tax ID input."""
    user = update.effective_user
    tax_id = update.message.text.strip()
    
    is_valid, error_msg = validate_thai_tax_id(tax_id)
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    if not is_valid:
        conversation.retry_count += 1
        if conversation.retry_count >= settings.max_retry_attempts:
            await repository.delete_conversation(user.id)
            await update.message.reply_text(messages.MAX_RETRIES_EXCEEDED, parse_mode='Markdown')
            return ConversationHandler.END
        
        await repository.save_conversation_state(user.id, conversation)
        await update.message.reply_text(
            messages.INVALID_TAX_ID_ERROR.format(
                error_message=error_msg,
                attempt=conversation.retry_count,
                max_attempts=settings.max_retry_attempts
            ),
            parse_mode='Markdown'
        )
        return ConversationState.BUYER_TAX_ID
    
    conversation.buyer_tax_id = tax_id
    conversation.retry_count = 0
    conversation.current_state = str(ConversationState.BUYER_NAME)
    await repository.save_conversation_state(user.id, conversation)
    
    step, total = get_state_progress(ConversationState.BUYER_NAME)
    await update.message.reply_text(
        messages.BUYER_NAME_PROMPT.format(step=step, total=total),
        parse_mode='Markdown'
    )
    
    return ConversationState.BUYER_NAME


async def handle_buyer_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle buyer name input."""
    user = update.effective_user
    name = update.message.text.strip()
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    conversation.buyer_name = name
    conversation.current_state = str(ConversationState.BUYER_ADDRESS)
    await repository.save_conversation_state(user.id, conversation)
    
    step, total = get_state_progress(ConversationState.BUYER_ADDRESS)
    await update.message.reply_text(
        messages.BUYER_ADDRESS_PROMPT.format(step=step, total=total),
        parse_mode='Markdown'
    )
    
    return ConversationState.BUYER_ADDRESS


async def handle_buyer_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle buyer address input."""
    user = update.effective_user
    address = update.message.text.strip()
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    conversation.buyer_address = address
    conversation.current_state = str(ConversationState.BUYER_BRANCH)
    await repository.save_conversation_state(user.id, conversation)
    
    step, total = get_state_progress(ConversationState.BUYER_BRANCH)
    await update.message.reply_text(
        messages.BUYER_BRANCH_PROMPT.format(step=step, total=total),
        parse_mode='Markdown'
    )
    
    return ConversationState.BUYER_BRANCH


async def handle_buyer_branch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle buyer branch code input."""
    user = update.effective_user
    branch_code = update.message.text.strip()
    
    is_valid, error_msg = validate_branch_code(branch_code)
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    if not is_valid:
        conversation.retry_count += 1
        if conversation.retry_count >= settings.max_retry_attempts:
            await repository.delete_conversation(user.id)
            await update.message.reply_text(messages.MAX_RETRIES_EXCEEDED, parse_mode='Markdown')
            return ConversationHandler.END
        
        await repository.save_conversation_state(user.id, conversation)
        await update.message.reply_text(
            messages.INVALID_BRANCH_CODE_ERROR.format(
                error_message=error_msg,
                attempt=conversation.retry_count,
                max_attempts=settings.max_retry_attempts
            ),
            parse_mode='Markdown'
        )
        return ConversationState.BUYER_BRANCH
    
    conversation.buyer_branch = branch_code
    conversation.retry_count = 0
    conversation.current_state = str(ConversationState.ITEM_DESCRIPTION)
    await repository.save_conversation_state(user.id, conversation)
    
    step, total = get_state_progress(ConversationState.ITEM_DESCRIPTION)
    await update.message.reply_text(
        messages.ITEM_DESCRIPTION_PROMPT.format(step=step, total=total),
        parse_mode='Markdown'
    )
    
    return ConversationState.ITEM_DESCRIPTION


# Invoice Item Handlers

async def handle_item_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle item description input."""
    user = update.effective_user
    description = update.message.text.strip()
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    conversation.current_item = {"description": description}
    conversation.current_state = str(ConversationState.ITEM_QUANTITY)
    await repository.save_conversation_state(user.id, conversation)
    
    await update.message.reply_text(
        messages.ITEM_QUANTITY_PROMPT,
        parse_mode='Markdown'
    )
    
    return ConversationState.ITEM_QUANTITY


async def handle_item_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle item quantity input."""
    user = update.effective_user
    quantity_str = update.message.text.strip()
    
    is_valid, error_msg, quantity = validate_quantity(quantity_str)
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    if not is_valid:
        conversation.retry_count += 1
        if conversation.retry_count >= settings.max_retry_attempts:
            await repository.delete_conversation(user.id)
            await update.message.reply_text(messages.MAX_RETRIES_EXCEEDED, parse_mode='Markdown')
            return ConversationHandler.END
        
        await repository.save_conversation_state(user.id, conversation)
        await update.message.reply_text(
            messages.INVALID_QUANTITY_ERROR.format(
                error_message=error_msg,
                attempt=conversation.retry_count,
                max_attempts=settings.max_retry_attempts
            ),
            parse_mode='Markdown'
        )
        return ConversationState.ITEM_QUANTITY
    
    conversation.current_item["quantity"] = str(quantity)
    conversation.retry_count = 0
    conversation.current_state = str(ConversationState.ITEM_PRICE)
    await repository.save_conversation_state(user.id, conversation)
    
    await update.message.reply_text(
        messages.ITEM_PRICE_PROMPT,
        parse_mode='Markdown'
    )
    
    return ConversationState.ITEM_PRICE


async def handle_item_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle item unit price input."""
    user = update.effective_user
    price_str = update.message.text.strip()
    
    is_valid, error_msg, price = validate_amount(price_str)
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    if not is_valid:
        conversation.retry_count += 1
        if conversation.retry_count >= settings.max_retry_attempts:
            await repository.delete_conversation(user.id)
            await update.message.reply_text(messages.MAX_RETRIES_EXCEEDED, parse_mode='Markdown')
            return ConversationHandler.END
        
        await repository.save_conversation_state(user.id, conversation)
        await update.message.reply_text(
            messages.INVALID_AMOUNT_ERROR.format(
                error_message=error_msg,
                attempt=conversation.retry_count,
                max_attempts=settings.max_retry_attempts
            ),
            parse_mode='Markdown'
        )
        return ConversationState.ITEM_PRICE
    
    conversation.current_item["unit_price"] = str(price)
    conversation.retry_count = 0
    conversation.current_state = str(ConversationState.ITEM_DISCOUNT)
    await repository.save_conversation_state(user.id, conversation)
    
    # Calculate max discount (quantity * price)
    qty = Decimal(conversation.current_item["quantity"])
    max_discount = qty * price
    
    await update.message.reply_text(
        messages.ITEM_DISCOUNT_PROMPT.format(max_discount=format_thai_currency(max_discount)),
        parse_mode='Markdown'
    )
    
    return ConversationState.ITEM_DISCOUNT


async def handle_item_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle item discount input."""
    user = update.effective_user
    discount_str = update.message.text.strip()
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    # Calculate max discount
    qty = Decimal(conversation.current_item["quantity"])
    price = Decimal(conversation.current_item["unit_price"])
    max_discount = qty * price
    
    is_valid, error_msg, discount = validate_discount(discount_str, max_discount)
    
    if not is_valid:
        conversation.retry_count += 1
        if conversation.retry_count >= settings.max_retry_attempts:
            await repository.delete_conversation(user.id)
            await update.message.reply_text(messages.MAX_RETRIES_EXCEEDED, parse_mode='Markdown')
            return ConversationHandler.END
        
        await repository.save_conversation_state(user.id, conversation)
        await update.message.reply_text(
            messages.INVALID_AMOUNT_ERROR.format(
                error_message=error_msg,
                attempt=conversation.retry_count,
                max_attempts=settings.max_retry_attempts
            ),
            parse_mode='Markdown'
        )
        return ConversationState.ITEM_DISCOUNT
    
    # Add item to list
    conversation.current_item["discount"] = str(discount)
    conversation.items.append(conversation.current_item.copy())
    line_total = (qty * price) - discount
    
    conversation.retry_count = 0
    conversation.current_state = str(ConversationState.ADD_MORE_ITEMS)
    await repository.save_conversation_state(user.id, conversation)
    
    # Ask if user wants to add more items
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Another Item", callback_data="add_item"),
            InlineKeyboardButton("✅ Continue", callback_data="no_more_items")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        messages.ADD_MORE_ITEMS_PROMPT.format(
            description=conversation.current_item["description"],
            quantity=qty,
            price=format_thai_currency(price),
            discount=format_thai_currency(discount),
            total=format_thai_currency(line_total)
        ),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Clear current item
    conversation.current_item = {}
    await repository.save_conversation_state(user.id, conversation)
    
    return ConversationState.ADD_MORE_ITEMS


async def handle_add_more_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle add more items callback."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    conversation = await repository.get_conversation_state(user.id)
    
    if not conversation:
        await query.edit_message_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    if query.data == "add_item":
        # Add another item
        conversation.current_state = str(ConversationState.ITEM_DESCRIPTION)
        await repository.save_conversation_state(user.id, conversation)
        
        step, total = get_state_progress(ConversationState.ITEM_DESCRIPTION)
        await query.edit_message_text(
            messages.ITEM_DESCRIPTION_PROMPT.format(step=step, total=total),
            parse_mode='Markdown'
        )
        return ConversationState.ITEM_DESCRIPTION
    
    else:  # no_more_items
        # Move to notes
        conversation.current_state = str(ConversationState.NOTES)
        await repository.save_conversation_state(user.id, conversation)
        
        step, total = get_state_progress(ConversationState.NOTES)
        await query.edit_message_text(
            messages.NOTES_PROMPT.format(step=step, total=total),
            parse_mode='Markdown'
        )
        return ConversationState.NOTES


# Notes and Confirmation Handlers

async def handle_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle notes input."""
    user = update.effective_user
    
    conversation = await repository.get_conversation_state(user.id)
    if not conversation:
        await update.message.reply_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    # Check for skip command
    if update.message.text.strip().lower() == "/skip":
        notes = None
    else:
        notes = update.message.text.strip()
    
    conversation.notes = notes
    conversation.current_state = str(ConversationState.CONFIRM)
    await repository.save_conversation_state(user.id, conversation)
    
    # Generate confirmation message
    try:
        invoice = conversation.to_invoice()
        summary = messages.format_invoice_summary(invoice, conversation.items)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_invoice")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        step, total = get_state_progress(ConversationState.CONFIRM)
        await update.message.reply_text(
            messages.CONFIRM_PROMPT.format(step=step, total=total, invoice_summary=summary),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return ConversationState.CONFIRM
    
    except Exception as e:
        logger.error("confirmation_error", user_id=user.id, error=str(e))
        await update.message.reply_text(
            f"Error creating invoice preview: {str(e)}\nPlease /start again."
        )
        await repository.delete_conversation(user.id)
        return ConversationHandler.END


async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation callback."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    conversation = await repository.get_conversation_state(user.id)
    
    if not conversation:
        await query.edit_message_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    if query.data == "cancel_invoice":
        await repository.delete_conversation(user.id)
        await query.edit_message_text(messages.CANCEL_MESSAGE, parse_mode='Markdown')
        return ConversationHandler.END
    
    # Confirm - generate invoice
    try:
        invoice = conversation.to_invoice()
        await query.edit_message_text("⏳ Creating document, please wait...")
        
        # Call invoice service (creates and signs document)
        success, response = await invoice_service.generate_invoice(invoice)
        
        if success:
            # Save to history
            await repository.save_invoice_history(user.id, invoice, response)
            await repository.delete_conversation(user.id)
            
            document_id = response.get('document_id', 'N/A')
            invoice_number = response.get('invoice_number', 'N/A')
            
            # Send success message
            await query.message.reply_text(
                messages.INVOICE_GENERATED_SUCCESS.format(
                    response_info=f"✅ Document created and signed successfully\n📝 Invoice Number: {invoice_number}\n🆔 Document ID: {document_id}"
                ),
                parse_mode='Markdown'
            )
            
            # Download and send PDF
            try:
                await query.message.reply_text("📄 Preparing your invoice PDF...")
                
                pdf_success, pdf_bytes = await invoice_service.download_pdf(document_id)
                
                if pdf_success and pdf_bytes:
                    # Send PDF as document using BytesIO
                    pdf_file = BytesIO(pdf_bytes)
                    pdf_file.name = f"{invoice_number}.pdf"
                    
                    await context.bot.send_document(
                        chat_id=user.id,
                        document=pdf_file,
                        filename=f"{invoice_number}.pdf",
                        caption=f"📄 Invoice: {invoice_number}",
                    )
                    logger.info("pdf_sent_successfully", user_id=user.id, document_id=document_id)
                else:
                    await query.message.reply_text(
                        "⚠️ PDF download failed. You can download it later from the web interface.",
                        parse_mode='Markdown'
                    )
                    logger.warning("pdf_download_failed", user_id=user.id, document_id=document_id)
                    
            except Exception as pdf_error:
                logger.error("pdf_send_error", user_id=user.id, error=str(pdf_error))
                await query.message.reply_text(
                    "⚠️ Failed to send PDF. You can download it from the web interface.",
                    parse_mode='Markdown'
                )
        else:
            error_msg = response.get('error', 'Unknown error occurred')
            error_details = response.get('details', {})
            full_error = f"{error_msg}"
            if isinstance(error_details, dict) and error_details.get('message'):
                full_error += f"\nDetails: {error_details['message']}"
            
            await query.message.reply_text(
                messages.INVOICE_GENERATION_ERROR.format(error_message=full_error),
                parse_mode='Markdown'
            )
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error("invoice_generation_error", user_id=user.id, error=str(e))
        await query.message.reply_text(
            messages.INVOICE_GENERATION_ERROR.format(error_message=str(e)),
            parse_mode='Markdown'
        )
        return ConversationHandler.END


# Conversation Handler Setup

def get_conversation_handler() -> ConversationHandler:
    """Create and return the conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            # Seller info handlers removed - now auto-populated from settings API
            ConversationState.BUYER_TAX_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buyer_tax_id)
            ],
            ConversationState.BUYER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buyer_name)
            ],
            ConversationState.BUYER_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buyer_address)
            ],
            ConversationState.BUYER_BRANCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buyer_branch)
            ],
            ConversationState.ITEM_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_description)
            ],
            ConversationState.ITEM_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_quantity)
            ],
            ConversationState.ITEM_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_price)
            ],
            ConversationState.ITEM_DISCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_discount)
            ],
            ConversationState.ADD_MORE_ITEMS: [
                CallbackQueryHandler(handle_add_more_items)
            ],
            ConversationState.NOTES: [
                MessageHandler(filters.TEXT, handle_notes)
            ],
            ConversationState.CONFIRM: [
                CallbackQueryHandler(handle_confirmation)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CommandHandler("help", help_command)
        ],
        name="invoice_conversation",
        persistent=False
    )
