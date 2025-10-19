# 🚀 Quick Start Guide - AI Intelligence Layer

## ⚡ 60-Second Setup

### 1. Get Gemini API Key
Visit: https://makersuite.google.com/app/apikey

### 2. Configure
```bash
cd ai_intelligence_layer
nano .env
# Add your API key: GEMINI_API_KEY=your_key_here
```

### 3. Run
```bash
source myenv/bin/activate
python main.py
```

Service starts on: http://localhost:9000

---

## 🧪 Quick Test

### Health Check
```bash
curl http://localhost:9000/api/health
```

### Full Test
```bash
./test_api.sh
```

---

## 📡 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/ingest/enriched` | POST | Webhook receiver |
| `/api/strategy/brainstorm` | POST | Generate 20 strategies |
| `/api/strategy/analyze` | POST | Select top 3 |

---

## 🔗 Integration

### With Enrichment Service (localhost:8000)

**Option 1: Pull** (AI fetches)
```bash
# In enrichment service, AI will auto-fetch from:
# http://localhost:8000/enriched?limit=10
```

**Option 2: Push** (Webhook - RECOMMENDED)
```bash
# In enrichment service .env:
NEXT_STAGE_CALLBACK_URL=http://localhost:9000/api/ingest/enriched
```

---

## 📦 What You Get

### Input
- Enriched telemetry (aero, tires, ERS, fuel, consistency)
- Race context (track, position, competitors)

### Output
- **20 diverse strategies** (conservative → aggressive)
- **Top 3 analyzed** with:
  - Win probabilities
  - Risk assessment
  - Engineer briefs
  - Driver radio scripts
  - ECU commands

---

## 🎯 Example Usage

### Brainstorm
```bash
curl -X POST http://localhost:9000/api/strategy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "race_context": {
      "race_info": {"track_name": "Monaco", "current_lap": 27, "total_laps": 58},
      "driver_state": {"driver_name": "Hamilton", "current_position": 4}
    }
  }'
```

### Analyze
```bash
curl -X POST http://localhost:9000/api/strategy/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "race_context": {...},
    "strategies": [...]
  }'
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| API key error | Add `GEMINI_API_KEY` to `.env` |
| Enrichment unreachable | Start enrichment service or provide telemetry data |
| Import errors | Activate venv: `source myenv/bin/activate` |

---

## 📚 Documentation

- **Full docs**: `README.md`
- **Implementation details**: `IMPLEMENTATION_SUMMARY.md`
- **Sample data**: `sample_data/`

---

## ✅ Status

All systems operational! Ready to generate race strategies! 🏎️💨
