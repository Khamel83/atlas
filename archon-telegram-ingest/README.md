# Archon Telegram Ingest Service

iOS → Telegram → Atlas content ingestion pipeline.

## Overview

This service provides a reliable, Shortcuts-free way to send URLs from iOS to Atlas via Telegram.

**Flow:**
1. iOS: Share → Telegram → Your Bot
2. OCI: Telegram webhook → FastAPI service → Atlas ingest
3. Result: URL stored in Atlas automatically

## Features

- ✅ Native iOS share sheet integration (no Shortcuts)
- ✅ Reliable delivery with Telegram's infrastructure
- ✅ Secure webhook with secret path and user whitelist
- ✅ systemd service for 100% uptime
- ✅ HTTPS via Caddy reverse proxy
- ✅ Comprehensive logging and error handling

## Architecture

```
iPhone App
    ↓ (Share Sheet)
Telegram
    ↓ (Bot API)
OCI Instance
    ↓ (webhook: /telegram/SECRET)
FastAPI Service (port 8081)
    ↓ (HTTP POST)
Atlas Ingest API
```

## Quick Start

1. **Setup on OCI**: Run the deployment script
2. **Configure Telegram**: Set webhook URL
3. **iOS Setup**: Pin bot in Telegram for easy access
4. **Usage**: Share any URL → Telegram → Your Bot → Done!

## Files

- `telegram_webhook.py` - Main FastAPI service
- `deploy.sh` - Complete OCI deployment script
- `archon-tg.service` - systemd service definition
- `Caddyfile.example` - HTTPS reverse proxy config
- `.env.example` - Environment variables template

## Credentials Required

```bash
TELEGRAM_BOT_TOKEN=8208417039:AAFLpW5zfByJEvROgPuirHoH_BGMjmDXwvA
TELEGRAM_CHAT_ID=7884781716
ATLAS_URL=https://atlas.khamel.com
WEBHOOK_SECRET=your-random-secret-path
DOMAIN=your.domain.com
```