FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p temp_photos docs

# Create service account from env var and start bot
CMD echo "$GOOGLE_SERVICE_ACCOUNT_JSON" > service-account.json && python bot.py