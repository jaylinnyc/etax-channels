# Quick Start Guide

## Prerequisites

Before you begin, make sure you have:

1. **Docker and Docker Compose** installed
2. **Telegram Bot Token** from [@BotFather](https://t.me/botfather)

## Getting Your Bot Token

1. Open Telegram and search for @BotFather
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token provided (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Setup Steps

### 1. Configure Environment Variables

Edit the `.env` file and add your bot token:

```bash
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
```

### 2. Start the Bot with Docker

```bash
docker-compose up --build
```

To run in background:
```bash
docker-compose up -d --build
```

### 3. Test the Bot

1. Open Telegram
2. Search for your bot by username (the one you created with @BotFather)
3. Send `/start` to begin creating an invoice

## Development Setup (Optional)

If you want to run the bot locally without Docker:

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Redis Locally

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 5. Update .env for Local Development

```
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
```

### 6. Run the Bot

```bash
python src/main.py
```

## Running Tests

```bash
# Install test dependencies (if not already installed)
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_validators.py
```

## Viewing Logs

### Docker Logs

```bash
# Follow logs in real-time
docker-compose logs -f bot

# View last 100 lines
docker-compose logs --tail=100 bot
```

## Stopping the Bot

```bash
# Stop and remove containers
docker-compose down

# Stop, remove containers, and delete volumes
docker-compose down -v
```

## Troubleshooting

### Bot not responding

1. Check logs: `docker-compose logs bot`
2. Verify bot token is correct in `.env`
3. Ensure Redis is running: `docker-compose ps`

### Redis connection error

1. Check Redis is running: `docker-compose ps`
2. Check Redis logs: `docker-compose logs redis`
3. Restart services: `docker-compose restart`

### Invoice service connection error

1. Verify `INVOICE_SERVICE_URL` in `.env` is correct
2. Ensure the invoice service is accessible from the bot container
3. Check network connectivity: add the invoice service to the same Docker network

## Bot Commands

- `/start` - Start creating a new invoice
- `/cancel` - Cancel current invoice creation
- `/help` - Show help message

## Next Steps

1. **Customize the JSON format**: Update `Invoice.to_service_format()` in [src/models/invoice.py](src/models/invoice.py) to match your exact API requirements

2. **Add authentication** (if needed): Modify [src/services/invoice_client.py](src/services/invoice_client.py) to include API keys or tokens

3. **Customize messages**: Edit [src/bot/messages.py](src/bot/messages.py) to change bot messages

4. **Add user restrictions**: Implement user whitelist in [src/bot/handlers.py](src/bot/handlers.py)

## Project Structure

```
etax-telegram-bot/
├── src/
│   ├── bot/              # Bot handlers and messages
│   ├── database/         # Redis client and repository
│   ├── models/           # Data models (Pydantic)
│   ├── services/         # External service clients
│   ├── validators/       # Input validators
│   ├── config.py         # Configuration management
│   └── main.py           # Main entry point
├── tests/                # Unit tests
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Bot container image
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables
```

## Support

For issues or questions:
1. Check the logs first
2. Review the README.md
3. Examine the code comments in relevant files
