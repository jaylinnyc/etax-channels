# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# Copy requirements first for better caching
COPY --chown=botuser:botuser requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=botuser:botuser src/ ./src/

# Switch to non-root user
USER botuser

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the bot
CMD ["python", "src/main.py"]
