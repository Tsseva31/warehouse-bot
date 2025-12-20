#!/bin/bash
set -e

# Create service account file from env var
echo "$GOOGLE_SERVICE_ACCOUNT_JSON" > service-account.json

# Start the bot
python bot.py