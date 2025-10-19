# Render.com Deployment Guide

## Quick Start

### 1. Render.com Configuration

**Service Type:** Web Service

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command (choose one):**

#### Option A: Shell Script (Recommended)
```bash
./start.sh
```

#### Option B: Python Supervisor
```bash
python start.py
```

#### Option C: Direct Command
```bash
python scripts/serve.py & python ai_intelligence_layer/main.py
```

### 2. Environment Variables

Set these in Render.com dashboard:

**Required:**
```bash
GEMINI_API_KEY=your_gemini_api_key_here
ENVIRONMENT=production
PRODUCTION_URL=https://your-app-name.onrender.com  # Your Render app URL
```

**Optional:**
```bash
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here  # For voice features
GEMINI_MODEL=gemini-2.5-flash
STRATEGY_COUNT=3
FAST_MODE=true
```

**Auto-configured (no need to set):**
```bash
# These are handled automatically by the config system
AI_SERVICE_PORT=9000
AI_SERVICE_HOST=0.0.0.0
ENRICHMENT_SERVICE_URL=http://localhost:8000  # Internal communication
```

### Important: Production URL

After deploying to Render, you'll get a URL like:
```
https://your-app-name.onrender.com
```

**You MUST set this URL in the environment variables:**
1. Go to Render dashboard → your service → Environment
2. Add: `PRODUCTION_URL=https://your-app-name.onrender.com`
3. The app will automatically use this for WebSocket connections and API URLs

### 3. Health Check

**Health Check Path:** `/health` (on port 9000)

**Health Check Command:**
```bash
curl http://localhost:9000/health
```

### 4. Port Configuration

- **Enrichment Service:** 8000 (internal)
- **AI Intelligence Layer:** 9000 (external, Render will expose this)

Render will automatically bind to `PORT` environment variable.

### 5. Files Required

- ✅ `start.sh` - Shell startup script
- ✅ `start.py` - Python startup supervisor
- ✅ `Procfile` - Render configuration
- ✅ `requirements.txt` - Python dependencies

### 6. Testing Locally

Test the startup script before deploying:

```bash
# Make executable
chmod +x start.sh

# Run locally
./start.sh
```

Or with Python supervisor:

```bash
python start.py
```

### 7. Deployment Steps

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Add Render deployment configuration"
   git push
   ```

2. **Create Render Service:**
   - Go to [render.com](https://render.com)
   - New → Web Service
   - Connect your GitHub repository
   - Select branch (main)

3. **Configure Service:**
   - Name: `hpc-simulation-ai`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `./start.sh`

4. **Add Environment Variables:**
   - `GEMINI_API_KEY`
   - `ELEVENLABS_API_KEY` (optional)

5. **Deploy!** 🚀

### 8. Monitoring

Check logs in Render dashboard for:
- `📊 Starting Enrichment Service on port 8000...`
- `🤖 Starting AI Intelligence Layer on port 9000...`
- `✨ All services running!`

### 9. Connecting Clients

**WebSocket URL:**
```
wss://your-app-name.onrender.com/ws/pi
```

**Enrichment API:**
```
https://your-app-name.onrender.com/ingest/telemetry
```

### 10. Troubleshooting

**Services won't start:**
- Check environment variables are set
- Verify `start.sh` is executable: `chmod +x start.sh`
- Check build logs for dependency issues

**Port conflicts:**
- Render will set `PORT` automatically (9000 by default)
- Services bind to `0.0.0.0` for external access

**Memory issues:**
- Consider Render's paid plans for more resources
- Free tier may struggle with AI model loading

## Architecture on Render

```
┌─────────────────────────────────────┐
│      Render.com Container           │
├─────────────────────────────────────┤
│                                     │
│  ┌───────────────────────────────┐ │
│  │   start.sh / start.py         │ │
│  └──────────┬────────────────────┘ │
│             │                       │
│    ┌────────┴─────────┐            │
│    │                  │            │
│    ▼                  ▼            │
│  ┌──────────┐   ┌──────────────┐  │
│  │Enrichment│   │AI Intelligence│  │
│  │Service   │   │Layer          │  │
│  │:8000     │◄──│:9000          │  │
│  └──────────┘   └──────┬────────┘  │
│                        │            │
└────────────────────────┼────────────┘
                         │
                    Internet
                         │
                    ┌────▼─────┐
                    │ Client   │
                    │(Pi/Web)  │
                    └──────────┘
```

## Next Steps

1. Test locally with `./start.sh`
2. Commit and push to GitHub
3. Create Render service
4. Configure environment variables
5. Deploy and monitor logs
6. Update client connection URLs

Good luck! 🎉
