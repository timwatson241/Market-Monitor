# Market Monitor

Automated cryptocurrency and stock market monitoring system that sends SMS alerts when significant price changes occur.

## Features

- Monitors multiple assets every 5 minutes:
  - S&P 500
  - Bitcoin (CAD)
  - Ethereum (CAD)
  - Solana (CAD)
- Sends SMS alerts for price drops (5%, 10%, 15%, 20%, 25% from weekly highs)
- Runs continuously on fly.io
- Uses Twilio for SMS notifications

## Prerequisites

- Python 3.9+
- fly.io account
- Twilio account
- Docker (for local testing)

## Environment Variables

Required environment variables:

```
TWILIO_SID=your_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE=your_twilio_phone
USER_PHONE=your_phone_number
CHECK_INTERVAL=300
PRICE_HISTORY_HOURS=3
STORAGE_PATH=/app/market_data.json
```

## Deployment

1. Install flyctl:

```bash
brew install flyctl
```

2. Login to fly.io:

```bash
flyctl auth login
```

3. Deploy:

```bash
flyctl launch
flyctl deploy
```

## Monitoring

Check application status:

```bash
flyctl status
```

View logs:

```bash
flyctl logs
```

## Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set environment variables
3. Run:

```bash
python market_monitor.py
```

## Cost Considerations

- fly.io: ~$5/month ($2.50 primary + $2.50 standby machine)
- Twilio: ~$0.0079 per SMS alert
