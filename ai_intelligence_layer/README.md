r# F1 AI Intelligence Layer

**The core innovation of our HPC-powered race strategy system**

This service transforms enriched telemetry data from HPC simulations into actionable F1 race strategies using advanced AI. It sits between the HPC enrichment module and race engineers, providing real-time strategic recommendations.

## 🎯 System Overview

The AI Intelligence Layer uses a **two-step LLM process** powered by Google Gemini:

1. **Strategy Generation (Brainstorming)**: Generate 20 diverse strategy options based on telemetry trends
2. **Strategy Analysis & Selection**: Analyze all options and select top 3 with detailed execution plans

## 🏗️ Architecture Integration

```
┌─────────────────────┐
│  HPC Enrichment     │
│  (localhost:8000)   │
│                     │
│  Enriched Telemetry │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  AI Intelligence    │  ◄── You are here
│  (localhost:9000)   │
│                     │
│  Strategy AI        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Race Engineers     │
│  Frontend/Display   │
└─────────────────────┘
```

### Upstream Service (HPC Enrichment)
- **URL**: http://localhost:8000
- **Provides**: Enriched telemetry data (lap-by-lap metrics)
- **Integration**: Pull (fetch) or Push (webhook)

### This Service (AI Intelligence Layer)
- **URL**: http://localhost:9000
- **Provides**: Strategic race recommendations with detailed analysis

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- HPC enrichment service running on port 8000

### 2. Installation

```bash
cd ai_intelligence_layer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Gemini API key
nano .env
```

Required environment variables:
```bash
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-1.5-pro
AI_SERVICE_PORT=9000
ENRICHMENT_SERVICE_URL=http://localhost:8000
```

### 4. Run the Service

```bash
# Start the server
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 9000 --reload
```

The service will be available at http://localhost:9000

## 📡 API Endpoints

### Health Check
```bash
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "AI Intelligence Layer",
  "version": "1.0.0",
  "demo_mode": false,
  "enrichment_service_url": "http://localhost:8000"
}
```

### Webhook Receiver (for enrichment service)
```bash
POST /api/ingest/enriched
Content-Type: application/json

{
  "lap": 27,
  "aero_efficiency": 0.83,
  "tire_degradation_index": 0.65,
  "ers_charge": 0.72,
  "fuel_optimization_score": 0.91,
  "driver_consistency": 0.89,
  "weather_impact": "medium"
}
```

**Response:**
```json
{
  "status": "received",
  "lap": 27,
  "buffer_size": 10
}
```

### Strategy Brainstorming
```bash
POST /api/strategy/brainstorm
Content-Type: application/json

{
  "enriched_telemetry": [...],  # Optional, will fetch from enrichment service if omitted
  "race_context": {
    "race_info": {
      "track_name": "Monaco",
      "total_laps": 58,
      "current_lap": 27,
      "weather_condition": "Dry",
      "track_temp_celsius": 42
    },
    "driver_state": {
      "driver_name": "Hamilton",
      "current_position": 4,
      "current_tire_compound": "medium",
      "tire_age_laps": 14,
      "fuel_remaining_percent": 47
    },
    "competitors": [...]
  }
}
```

**Response:**
```json
{
  "strategies": [
    {
      "strategy_id": 1,
      "strategy_name": "Conservative 1-Stop",
      "stop_count": 1,
      "pit_laps": [32],
      "tire_sequence": ["medium", "hard"],
      "brief_description": "Extend mediums to lap 32, safe finish on hards",
      "risk_level": "low",
      "key_assumption": "Tire degradation stays below 0.85 until lap 32"
    }
    // ... 19 more strategies
  ]
}
```

### Strategy Analysis
```bash
POST /api/strategy/analyze
Content-Type: application/json

{
  "enriched_telemetry": [...],
  "race_context": {...},
  "strategies": [...]  # Array of 20 strategies from brainstorm
}
```

**Response:**
```json
{
  "top_strategies": [
    {
      "rank": 1,
      "strategy_id": 7,
      "strategy_name": "Aggressive Undercut",
      "classification": "RECOMMENDED",
      "predicted_outcome": {
        "finish_position_most_likely": 3,
        "p1_probability": 8,
        "p2_probability": 22,
        "p3_probability": 45,
        "p4_or_worse_probability": 25,
        "confidence_score": 78
      },
      "risk_assessment": {
        "risk_level": "medium",
        "key_risks": ["Requires pit stop under 2.5s"],
        "success_factors": ["Tire degradation trending favorably"]
      },
      "telemetry_insights": {
        "tire_wear_projection": "Current 0.65, will hit 0.85 cliff by lap 35",
        "aero_status": "0.83 - car performing well",
        "fuel_margin": "0.91 - excellent, no saving needed",
        "driver_form": "0.89 - high confidence"
      },
      "engineer_brief": {
        "title": "Recommended: Aggressive Undercut Lap 18",
        "summary": "67% chance P3 or better",
        "key_points": ["Tire degradation accelerating", "Undercut window open"],
        "execution_steps": ["Lap 18: Box for softs", "Lap 19-26: Push hard"]
      },
      "driver_audio_script": "Box this lap. Softs going on. Push mode for 8 laps.",
      "ecu_commands": {
        "fuel_mode": "RICH",
        "ers_strategy": "AGGRESSIVE_DEPLOY",
        "engine_mode": "PUSH",
        "brake_balance_adjustment": 0,
        "differential_setting": "BALANCED"
      }
    }
    // ... 2 more strategies (rank 2, 3)
  ],
  "situational_context": {
    "critical_decision_point": "Next 3 laps crucial",
    "telemetry_alert": "Aero efficiency stable",
    "key_assumption": "No safety car deployment",
    "time_sensitivity": "Decision needed within 2 laps"
  }
}
```

## 🧪 Testing

### Using the Test Script

```bash
cd ai_intelligence_layer
chmod +x test_api.sh
./test_api.sh
```

### Manual Testing with curl

```bash
# 1. Health check
curl http://localhost:9000/api/health

# 2. Brainstorm (with sample data)
curl -X POST http://localhost:9000/api/strategy/brainstorm \
  -H "Content-Type: application/json" \
  -d @- << EOF
{
  "enriched_telemetry": $(cat sample_data/sample_enriched_telemetry.json),
  "race_context": $(cat sample_data/sample_race_context.json)
}
EOF

# 3. Full workflow test
./test_api.sh
```

## 🔗 Integration with Enrichment Service

### Option 1: Pull Model (Service Fetches)

The AI service automatically fetches telemetry when none is provided:

```bash
# Configure enrichment service URL in .env
ENRICHMENT_SERVICE_URL=http://localhost:8000

# Call brainstorm without telemetry data
curl -X POST http://localhost:9000/api/strategy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{"race_context": {...}}'
```

### Option 2: Push Model (Webhook) **[RECOMMENDED]**

Configure the enrichment service to push data:

```bash
# In enrichment service .env:
NEXT_STAGE_CALLBACK_URL=http://localhost:9000/api/ingest/enriched

# Start enrichment service - it will automatically push to AI layer
# AI layer buffers the data for strategy generation
```

## 📊 Understanding Enriched Telemetry

The AI layer interprets enriched metrics from HPC analysis:

| Metric | Range | Interpretation | Strategy Impact |
|--------|-------|----------------|-----------------|
| `aero_efficiency` | 0-1 (higher better) | Aerodynamic performance | <0.6 = problem, prioritize early stop |
| `tire_degradation_index` | 0-1 (higher worse) | Tire wear | >0.7 = aggressive stop, >0.85 = cliff imminent |
| `ers_charge` | 0-1 | Energy system charge | >0.7 = can attack, <0.3 = depleted |
| `fuel_optimization_score` | 0-1 (higher better) | Fuel efficiency | <0.7 = must save fuel |
| `driver_consistency` | 0-1 (higher better) | Lap-to-lap variance | <0.75 = risky, prefer conservative |
| `weather_impact` | low/medium/high | Weather effect severity | high = favor flexible strategies |

## 🎓 How It Works

### Step 1: Strategy Brainstorming

The AI generates 20 diverse strategies by:
1. Analyzing telemetry trends (tire deg rate, aero efficiency, ERS patterns)
2. Considering race constraints (current lap, competitors, track)
3. Generating diverse options: conservative, standard, aggressive, reactive, contingency
4. Using high temperature (0.9) for creative diversity

**Diversity categories:**
- Conservative: 1-stop, minimal risk
- Standard: Balanced 1-stop or 2-stop
- Aggressive: Early undercut, overcut plays
- Reactive: Respond to competitor moves
- Contingency: Safety car, rain scenarios

### Step 2: Strategy Analysis

The AI analyzes all 20 strategies and selects top 3 by:
1. **Tire Degradation Projection**: Rate of change, cliff prediction
2. **Aero Efficiency Impact**: Lap time degradation assessment
3. **Fuel Management**: Fuel-saving mode necessity
4. **Driver Consistency**: Risk tolerance based on form
5. **Weather & Track Position**: Safety car probability, overtaking difficulty
6. **Competitor Analysis**: Undercut/overcut opportunities

**Selection criteria:**
- Rank 1 (RECOMMENDED): Highest podium probability, balanced risk
- Rank 2 (ALTERNATIVE): Different approach, viable if conditions change
- Rank 3 (CONSERVATIVE): Safest option, minimize finishing outside points

Uses low temperature (0.3) for analytical consistency.

## 🛠️ Development

### Project Structure

```
ai_intelligence_layer/
├── main.py                 # FastAPI application
├── config.py               # Settings management
├── requirements.txt        # Dependencies
├── .env.example            # Environment template
├── models/
│   ├── input_models.py     # Request schemas
│   ├── output_models.py    # Response schemas
│   └── internal_models.py  # Internal data structures
├── services/
│   ├── gemini_client.py    # Gemini API wrapper
│   ├── telemetry_client.py # Enrichment API client
│   ├── strategy_generator.py  # Brainstorm logic
│   └── strategy_analyzer.py   # Analysis logic
├── prompts/
│   ├── brainstorm_prompt.py   # Step 1 prompt template
│   └── analyze_prompt.py      # Step 2 prompt template
├── utils/
│   ├── validators.py       # Strategy validation
│   └── telemetry_buffer.py # In-memory storage
└── sample_data/
    ├── sample_enriched_telemetry.json
    └── sample_race_context.json
```

### Adding New Features

1. **Custom Strategy Types**: Edit `prompts/brainstorm_prompt.py`
2. **Analysis Criteria**: Edit `prompts/analyze_prompt.py`
3. **Telemetry Metrics**: Add to `models/input_models.py` and update validators
4. **Validation Rules**: Edit `utils/validators.py`

## ⚙️ Configuration Options

### Demo Mode

Enable consistent responses for demos:
```bash
DEMO_MODE=true
```

Features:
- Caches Gemini responses for identical inputs
- Lower temperature for repeatability
- Artificial "thinking" delays (optional)

### Performance Tuning

```bash
BRAINSTORM_TIMEOUT=30    # Seconds for brainstorm generation
ANALYZE_TIMEOUT=60       # Seconds for analysis
GEMINI_MAX_RETRIES=3     # Retry attempts on failure
```

### Gemini Model Selection

```bash
GEMINI_MODEL=gemini-1.5-pro        # Recommended
# GEMINI_MODEL=gemini-1.5-flash    # Faster, less detailed
```

## 🐛 Troubleshooting

### "Enrichment service unreachable"
- Check enrichment service is running: `curl http://localhost:8000/health`
- Verify `ENRICHMENT_SERVICE_URL` in `.env`
- Use absolute telemetry in request as fallback

### "Gemini API error"
- Verify `GEMINI_API_KEY` in `.env`
- Check API quota: https://makersuite.google.com/app/apikey
- Review rate limits (increase `GEMINI_MAX_RETRIES`)

### "Invalid JSON from Gemini"
- Service automatically retries with stricter prompt
- Check Gemini model supports JSON mode
- Review logs for parsing errors

### "Strategies validation failed"
- Check race context constraints (current lap, total laps)
- Ensure at least 2 tire compounds available
- Review strategy validator logs

## 📈 Performance

**Target response times:**
- Brainstorm: <5 seconds (20 strategies)
- Analyze: <10 seconds (top 3 selection)
- Health check: <100ms
- Webhook ingest: <50ms

**Optimization tips:**
- Use webhook push model for real-time data
- Enable demo mode for consistent demo performance
- Adjust timeouts based on network conditions

## 🔒 Security Notes

- Store `GEMINI_API_KEY` securely (never commit to git)
- Use environment variables for all secrets
- Consider API key rotation for production
- Implement rate limiting for public deployments

## 📝 License

Part of HPCSimSite hackathon project.

## 🤝 Contributing

This is a hackathon project. For improvements:
1. Test changes with sample data
2. Validate against race constraints
3. Ensure backward compatibility with enrichment service

## 📞 Support

For integration issues:
- Check enrichment service compatibility
- Review API endpoint documentation
- Test with provided sample data
- Enable debug logging: `LOG_LEVEL=DEBUG`

---

**Built for the HPC + AI Race Strategy Hackathon** 🏎️💨
