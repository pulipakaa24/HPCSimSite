# Environment Configuration Guide

## Overview

The HPC Simulation system automatically adapts between **development** and **production** environments based on the `ENVIRONMENT` variable.

## Configuration Files

### Development (Local)
- File: `.env` (in project root)
- `ENVIRONMENT=development`
- Uses `localhost` URLs

### Production (Render.com)
- Set environment variables in Render dashboard
- `ENVIRONMENT=production`
- `PRODUCTION_URL=https://your-app.onrender.com`
- Automatically adapts all URLs

## Key Environment Variables

### Required for Both Environments

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `ENVIRONMENT` | Environment mode | `development` or `production` |

### Production-Specific

| Variable | Description | Example |
|----------|-------------|---------|
| `PRODUCTION_URL` | Your Render.com app URL | `https://hpc-ai.onrender.com` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `ELEVENLABS_API_KEY` | - | Voice synthesis (optional) |
| `GEMINI_MODEL` | `gemini-1.5-pro` | AI model version |
| `STRATEGY_COUNT` | `3` | Strategies per lap |
| `FAST_MODE` | `true` | Use shorter prompts |

## How It Works

### URL Auto-Configuration

The `config.py` automatically provides environment-aware URLs:

```python
settings = get_settings()

# Automatically returns correct URL based on environment:
settings.base_url          # http://localhost:9000 OR https://your-app.onrender.com
settings.websocket_url     # ws://localhost:9000 OR wss://your-app.onrender.com
settings.internal_enrichment_url  # Always http://localhost:8000 (internal)
```

### Development Environment

```bash
ENVIRONMENT=development
# Result:
# - base_url: http://localhost:9000
# - websocket_url: ws://localhost:9000
# - Dashboard connects to: ws://localhost:9000/ws/dashboard
```

### Production Environment

```bash
ENVIRONMENT=production
PRODUCTION_URL=https://hpc-ai.onrender.com
# Result:
# - base_url: https://hpc-ai.onrender.com
# - websocket_url: wss://hpc-ai.onrender.com
# - Dashboard connects to: wss://hpc-ai.onrender.com/ws/dashboard
```

## Component-Specific Configuration

### 1. AI Intelligence Layer

**Development:**
- Binds to: `0.0.0.0:9000`
- Enrichment client connects to: `http://localhost:8000`
- Dashboard WebSocket: `ws://localhost:9000/ws/dashboard`

**Production:**
- Binds to: `0.0.0.0:9000` (Render exposes externally)
- Enrichment client connects to: `http://localhost:8000` (internal)
- Dashboard WebSocket: `wss://your-app.onrender.com/ws/dashboard`

### 2. Enrichment Service

**Development:**
- Binds to: `0.0.0.0:8000`
- Accessed at: `http://localhost:8000`

**Production:**
- Binds to: `0.0.0.0:8000` (internal only)
- Accessed internally at: `http://localhost:8000`
- Not exposed externally (behind AI layer)

### 3. Dashboard (Frontend)

**Auto-detects environment:**
```javascript
// Automatically uses current host and protocol
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const host = window.location.host;
const wsUrl = `${protocol}//${host}/ws/dashboard`;
```

### 4. Pi Simulator (Client)

**Development:**
```bash
python simulate_pi_websocket.py \
  --ws-url ws://localhost:9000/ws/pi \
  --enrichment-url http://localhost:8000
```

**Production:**
```bash
python simulate_pi_websocket.py \
  --ws-url wss://your-app.onrender.com/ws/pi \
  --enrichment-url https://your-app.onrender.com  # If exposed
```

## Quick Setup

### Local Development

1. **Create `.env` in project root:**
```bash
GEMINI_API_KEY=your_key_here
ENVIRONMENT=development
```

2. **Start services:**
```bash
./start.sh
```

### Render.com Production

1. **Set environment variables in Render dashboard:**
```
GEMINI_API_KEY=your_key_here
ENVIRONMENT=production
PRODUCTION_URL=https://your-app-name.onrender.com
```

2. **Deploy** - URLs auto-configure!

## Troubleshooting

### Issue: WebSocket connection fails in production

**Check:**
1. `ENVIRONMENT=production` is set
2. `PRODUCTION_URL` matches your actual Render URL (including `https://`)
3. Dashboard uses `wss://` protocol (should auto-detect)

### Issue: Enrichment service unreachable

**In production:**
- Both services run in same container
- Internal communication uses `http://localhost:8000`
- This is automatic, no configuration needed

**In development:**
- Ensure enrichment service is running: `python scripts/serve.py`
- Check `http://localhost:8000/health`

### Issue: Pi simulator can't connect

**Development:**
```bash
# Test connection
curl http://localhost:9000/health
wscat -c ws://localhost:9000/ws/pi
```

**Production:**
```bash
# Test connection
curl https://your-app.onrender.com/health
wscat -c wss://your-app.onrender.com/ws/pi
```

## Environment Variable Priority

1. **Render Environment Variables** (highest priority in production)
2. **.env file** (development)
3. **Default values** (in config.py)

## Best Practices

### Development
- ✅ Use `.env` file
- ✅ Keep `ENVIRONMENT=development`
- ✅ Use `localhost` URLs
- ❌ Don't commit `.env` to git

### Production
- ✅ Set all variables in Render dashboard
- ✅ Use `ENVIRONMENT=production`
- ✅ Set `PRODUCTION_URL` after deployment
- ✅ Use HTTPS/WSS protocols
- ❌ Don't hardcode URLs in code

## Example Configurations

### .env (Development)
```bash
GEMINI_API_KEY=AIzaSyDK_jxVlJUpzyxuiGcopSFkiqMAUD3-w0I
GEMINI_MODEL=gemini-2.5-flash
ENVIRONMENT=development
ELEVENLABS_API_KEY=your_key_here
STRATEGY_COUNT=3
FAST_MODE=true
```

### Render Environment Variables (Production)
```bash
GEMINI_API_KEY=AIzaSyDK_jxVlJUpzyxuiGcopSFkiqMAUD3-w0I
GEMINI_MODEL=gemini-2.5-flash
ENVIRONMENT=production
PRODUCTION_URL=https://hpc-simulation-ai.onrender.com
ELEVENLABS_API_KEY=your_key_here
STRATEGY_COUNT=3
FAST_MODE=true
```

## Migration Checklist

When deploying to production:

- [ ] Set `ENVIRONMENT=production` in Render
- [ ] Deploy and get Render URL
- [ ] Set `PRODUCTION_URL` with your Render URL
- [ ] Test health endpoint: `https://your-app.onrender.com/health`
- [ ] Test WebSocket: `wss://your-app.onrender.com/ws/pi`
- [ ] Open dashboard: `https://your-app.onrender.com/dashboard`
- [ ] Verify logs show production URLs

Done! The system will automatically use production URLs for all connections.
