"""Conversation states for the invoice bot."""
from enum import IntEnum, auto


class ConversationState(IntEnum):
    """Conversation states for invoice creation flow."""
    
    # Initial state
    START = auto()
    
    # Seller information
    SELLER_TAX_ID = auto()
    SELLER_NAME = auto()
    SELLER_ADDRESS = auto()
    SELLER_BRANCH = auto()
    
    # Buyer information
    BUYER_TAX_ID = auto()
    BUYER_NAME = auto()
    BUYER_ADDRESS = auto()
    BUYER_POSTAL_CODE = auto()
    BUYER_BRANCH = auto()
    
    # Invoice items
    ITEM_DESCRIPTION = auto()
    ITEM_QUANTITY = auto()
    ITEM_PRICE = auto()
    ITEM_DISCOUNT = auto()
    ADD_MORE_ITEMS = auto()
    
    # Final steps
    NOTES = auto()
    CONFIRM = auto()
    
    # End state
    END = auto()


# State flow mapping
# Note: Seller states are skipped as seller info is auto-populated from settings API
STATE_FLOW = {
    ConversationState.START: ConversationState.BUYER_TAX_ID,
    # Seller states kept for backwards compatibility but not used in main flow
    ConversationState.SELLER_TAX_ID: ConversationState.SELLER_NAME,
    ConversationState.SELLER_NAME: ConversationState.SELLER_ADDRESS,
    ConversationState.SELLER_ADDRESS: ConversationState.SELLER_BRANCH,
    ConversationState.SELLER_BRANCH: ConversationState.BUYER_TAX_ID,
    # Active flow starts here
    ConversationState.BUYER_TAX_ID: ConversationState.BUYER_NAME,
    ConversationState.BUYER_NAME: ConversationState.BUYER_ADDRESS,
    ConversationState.BUYER_ADDRESS: ConversationState.BUYER_POSTAL_CODE,
    ConversationState.BUYER_POSTAL_CODE: ConversationState.ITEM_DESCRIPTION,
    ConversationState.BUYER_BRANCH: ConversationState.ITEM_DESCRIPTION,  # Kept for backwards compatibility
    ConversationState.ITEM_DESCRIPTION: ConversationState.ITEM_QUANTITY,
    ConversationState.ITEM_QUANTITY: ConversationState.ITEM_PRICE,
    ConversationState.ITEM_PRICE: ConversationState.ITEM_DISCOUNT,
    ConversationState.ITEM_DISCOUNT: ConversationState.ADD_MORE_ITEMS,
    ConversationState.ADD_MORE_ITEMS: ConversationState.NOTES,  # If no more items
    ConversationState.NOTES: ConversationState.CONFIRM,
    ConversationState.CONFIRM: ConversationState.END,
}


def get_next_state(current_state: ConversationState) -> ConversationState:
    """Get the next state in the conversation flow.
    
    Args:
        current_state: Current conversation state
        
    Returns:
        Next state in the flow
    """
    return STATE_FLOW.get(current_state, ConversationState.END)


def get_state_progress(current_state: ConversationState) -> tuple[int, int]:
    """Get progress information for current state.
    
    Args:
        current_state: Current conversation state
        
    Returns:
        Tuple of (current_step, total_steps)
    """
    # Define major steps for progress tracking
    # Note: Seller info is now auto-populated from settings API
    # Note: Branch code is always 00000 (head office) for buyers
    major_steps = [
        ConversationState.BUYER_TAX_ID,
        ConversationState.BUYER_NAME,
        ConversationState.BUYER_ADDRESS,
        ConversationState.BUYER_POSTAL_CODE,
        ConversationState.ITEM_DESCRIPTION,
        ConversationState.ITEM_QUANTITY,
        ConversationState.ITEM_PRICE,
        ConversationState.NOTES,
        ConversationState.CONFIRM,
    ]
    
    try:
        current_step = major_steps.index(current_state) + 1
    except ValueError:
        current_step = 0
    
    return (current_step, len(major_steps))
