#!/bin/bash
# test_login.sh

# Load credentials from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Error: .env file not found. Please create it first."
    exit 1
fi

if [ -z "$EUFY_EMAIL" ] || [ -z "$EUFY_PASSWORD" ]; then
    echo "Error: EUFY_EMAIL or EUFY_PASSWORD not set in .env"
    exit 1
fi

echo "Testing login for $EUFY_EMAIL..."

RESPONSE=$(curl -s -X POST "https://api.eufylife.com/v1/user/v2/email/login" \
  -H "Accept: */*" \
  -H "Accept-Language: en-US,en;q=0.9" \
  -H "User-Agent: EufyLife-iOS-3.3.7" \
  -H "Category: Health" \
  -H "Language: en" \
  -H "Timezone: UTC" \
  -H "Country: US" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "eufy-app",
    "client_secret": "8FHf22gaTKu7MZXqz5zytw",
    "email": "'"$EUFY_EMAIL"'",
    "password": "'"$EUFY_PASSWORD"'"
  }')

RES_CODE=$(echo $RESPONSE | grep -o '"res_code":[0-9]*' | cut -d':' -f2)

if [ "$RES_CODE" = "1" ]; then
    echo "✅ Login SUCCESSFUL!"
else
    echo "❌ Login FAILED!"
    echo "Response: $RESPONSE"
fi
