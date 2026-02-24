"""Main entry point for the Thai E-Tax Invoice Telegram Bot."""
import asyncio
import sys
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)
import structlog
from structlog.processors import JSONRenderer

from src.config import settings
from src.bot.handlers import get_conversation_handler, help_command
from src.bot import messages
from src.database.redis_client import redis_client

# Configure structured logging
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        JSONRenderer() if settings.log_level == "DEBUG" else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        LOG_LEVEL_MAP.get(settings.log_level.upper(), logging.INFO)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def error_handler(update: object, context) -> None:
    """Handle errors in the bot."""
    logger.error("bot_error", error=str(context.error), update=update)
    
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred while processing your request. "
            "Please try again or contact support."
        )


async def post_init(application: Application) -> None:
    """Initialize resources after bot startup."""
    logger.info("bot_initializing")
    
    # Connect to Redis
    try:
        await redis_client.connect()
        logger.info("redis_connected")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise
    
    logger.info("bot_initialized", bot_username=application.bot.username)


async def post_shutdown(application: Application) -> None:
    """Cleanup resources on bot shutdown."""
    logger.info("bot_shutting_down")
    
    # Disconnect from Redis
    try:
        await redis_client.disconnect()
        logger.info("redis_disconnected")
    except Exception as e:
        logger.error("redis_disconnect_error", error=str(e))
    
    logger.info("bot_shutdown_complete")


async def unknown_command(update: Update, context) -> None:
    """Handle unknown commands."""
    await update.message.reply_text(
        "❓ Unknown command. Use /help to see available commands."
    )


def main() -> None:
    """Start the bot."""
    logger.info("starting_bot", log_level=settings.log_level)
    
    # Validate configuration
    if not settings.telegram_bot_token:
        logger.error("missing_bot_token")
        sys.exit(1)
    
    # Create the Application
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Add conversation handler
    conversation_handler = get_conversation_handler()
    application.add_handler(conversation_handler)
    
    # Add help command handler (outside conversation)
    application.add_handler(CommandHandler("help", help_command))
    
    # Add unknown command handler
    application.add_handler(
        MessageHandler(filters.COMMAND, unknown_command)
    )
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("bot_starting", bot_token=settings.telegram_bot_token[:10] + "...")
    
    try:
        # Run the bot until Ctrl-C
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logger.info("bot_stopped_by_user")
    except Exception as e:
        logger.error("bot_error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
