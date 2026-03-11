# Thai E-Tax Invoice Telegram Bot

A conversational Telegram bot that collects Thai tax invoice information from users, validates the data, and generates invoices through an external microservice.

## Features

- 📝 Step-by-step invoice data collection
- ✅ Thai Tax ID validation with checksum
- 💰 Amount and quantity validation
- 🔄 Multiple line items support
- 📊 Data confirmation before submission
- 🔄 Redis-based conversation state management
- 🐳 Docker containerized deployment

## Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Access to the invoice generation service

## Quick Start

1. **Clone the repository and navigate to the directory:**
   ```bash
   cd etax-telegram-bot
   ```

2. **Create a `.env` file from the example:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` and add your bot token:**
   ```
   TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
   ```

4. **Start the bot using Docker Compose:**
   ```bash
   docker-compose up -d
   ```

5. **View logs:**
   ```bash
   docker-compose logs -f bot
   ```

6. **Stop the bot:**
   ```bash
   docker-compose down
   ```

## Bot Commands

- `/start` - Start a new invoice creation
- `/cancel` - Cancel current conversation
- `/help` - Show usage instructions

## Bot Usage Flow

1. Send `/start` to begin
2. Provide seller information (Tax ID, Name, Address, Branch)
3. Provide buyer information (Tax ID, Name, Address, Branch)
4. Add invoice items (Description, Quantity, Unit Price, Discount)
5. Add more items or continue
6. Add optional notes
7. Confirm data
8. Receive invoice generation result

## Development

### Local Setup (without Docker)♣

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Redis locally:**
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

5. **Run the bot:**
   ```bash
   python src/main.py
   ```

### Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
etax-telegram-bot/
├── src/
│   ├── bot/
│   │   ├── handlers.py       # Conversation handlers
│   │   ├── states.py         # Conversation states
│   │   └── messages.py       # Bot messages
│   ├── database/
│   │   ├── redis_client.py   # Redis connection
│   │   └── repository.py     # Data access layer
│   ├── models/
│   │   └── invoice.py        # Pydantic models
│   ├── services/
│   │   └── invoice_client.py # Invoice service client
│   ├── validators/
│   │   └── thai_validators.py # Input validators
│   ├── config.py             # Configuration
│   └── main.py               # Main entry point
├── tests/
│   ├── test_validators.py
│   ├── test_models.py
│   └── test_conversation.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Configuration

All configuration is done through environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather | Required |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `INVOICE_SERVICE_URL` | Invoice generation service endpoint | `http://etax:9443/api/v1/xml` |
| `CONVERSATION_TIMEOUT` | Conversation expiry time (seconds) | `3600` |
| `INVOICE_HISTORY_TTL` | Invoice history retention (seconds) | `86400` |
| `MAX_RETRY_ATTEMPTS` | Max validation retry attempts | `3` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Thai Tax Invoice Fields

### Seller Information
- Tax ID (13 digits with checksum validation)
- Business Name
- Address
- Branch Code

### Buyer Information
- Tax ID (13 digits with checksum validation)
- Business Name
- Address
- Branch Code

### Invoice Items
- Description
- Quantity
- Unit Price (THB)
- Discount (optional)

### Calculated Fields
- Subtotal
- VAT Amount (7%)
- Total Amount

## License

MIT License

## Support

For issues and questions, please open an issue in the repository.
