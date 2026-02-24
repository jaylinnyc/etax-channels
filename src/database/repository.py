"""Data repository for Redis operations."""
import json
from typing import Optional, List
import structlog

from src.database.redis_client import redis_client
from src.models.invoice import ConversationData, Invoice
from src.config import settings

logger = structlog.get_logger()


class Repository:
    """Repository for managing conversation and invoice data in Redis."""
    
    @staticmethod
    def _conversation_key(user_id: int) -> str:
        """Generate Redis key for conversation data."""
        return f"conversation:{user_id}"
    
    @staticmethod
    def _invoice_history_key(user_id: int) -> str:
        """Generate Redis key for invoice history."""
        return f"invoice_history:{user_id}"
    
    async def save_conversation_state(
        self,
        user_id: int,
        conversation_data: ConversationData,
        ttl: Optional[int] = None
    ) -> None:
        """Save conversation state to Redis.
        
        Args:
            user_id: Telegram user ID
            conversation_data: Conversation data to save
            ttl: Time to live in seconds (default from settings)
        """
        if ttl is None:
            ttl = settings.conversation_timeout
        
        key = self._conversation_key(user_id)
        data = conversation_data.model_dump_json()
        
        try:
            await redis_client.client.setex(key, ttl, data)
            logger.debug(
                "conversation_saved",
                user_id=user_id,
                state=conversation_data.current_state,
                ttl=ttl
            )
        except Exception as e:
            logger.error("conversation_save_failed", user_id=user_id, error=str(e))
            raise
    
    async def get_conversation_state(self, user_id: int) -> Optional[ConversationData]:
        """Retrieve conversation state from Redis.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            ConversationData if exists, None otherwise
        """
        key = self._conversation_key(user_id)
        
        try:
            data = await redis_client.client.get(key)
            if data:
                logger.debug("conversation_retrieved", user_id=user_id)
                return ConversationData.model_validate_json(data)
            return None
        except Exception as e:
            logger.error("conversation_retrieve_failed", user_id=user_id, error=str(e))
            return None
    
    async def delete_conversation(self, user_id: int) -> None:
        """Delete conversation state from Redis.
        
        Args:
            user_id: Telegram user ID
        """
        key = self._conversation_key(user_id)
        
        try:
            await redis_client.client.delete(key)
            logger.debug("conversation_deleted", user_id=user_id)
        except Exception as e:
            logger.error("conversation_delete_failed", user_id=user_id, error=str(e))
    
    async def save_invoice_history(
        self,
        user_id: int,
        invoice: Invoice,
        response_data: Optional[dict] = None,
        ttl: Optional[int] = None
    ) -> None:
        """Save completed invoice to history.
        
        Args:
            user_id: Telegram user ID
            invoice: Invoice data
            response_data: Response from invoice service
            ttl: Time to live in seconds (default from settings)
        """
        if ttl is None:
            ttl = settings.invoice_history_ttl
        
        key = self._invoice_history_key(user_id)
        
        history_item = {
            "invoice": invoice.model_dump(mode='json'),
            "response": response_data,
            "timestamp": invoice.issue_date.isoformat()
        }
        
        try:
            # Add to list (prepend to front)
            await redis_client.client.lpush(key, json.dumps(history_item))
            
            # Trim list to keep only last 50 items
            await redis_client.client.ltrim(key, 0, 49)
            
            # Set expiry on key
            await redis_client.client.expire(key, ttl)
            
            logger.info("invoice_history_saved", user_id=user_id)
        except Exception as e:
            logger.error("invoice_history_save_failed", user_id=user_id, error=str(e))
    
    async def get_user_invoices(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[dict]:
        """Retrieve user's invoice history.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of invoices to retrieve
            
        Returns:
            List of invoice history items
        """
        key = self._invoice_history_key(user_id)
        
        try:
            items = await redis_client.client.lrange(key, 0, limit - 1)
            return [json.loads(item) for item in items]
        except Exception as e:
            logger.error("invoice_history_retrieve_failed", user_id=user_id, error=str(e))
            return []
    
    async def update_conversation_field(
        self,
        user_id: int,
        field_updates: dict
    ) -> Optional[ConversationData]:
        """Update specific fields in conversation data.
        
        Args:
            user_id: Telegram user ID
            field_updates: Dictionary of field names and values to update
            
        Returns:
            Updated ConversationData or None if not found
        """
        conversation = await self.get_conversation_state(user_id)
        if not conversation:
            return None
        
        # Update fields
        for field, value in field_updates.items():
            if hasattr(conversation, field):
                setattr(conversation, field, value)
        
        # Save updated conversation
        await self.save_conversation_state(user_id, conversation)
        return conversation


# Global repository instance
repository = Repository()
