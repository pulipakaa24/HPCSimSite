# System Architecture & Data Flow

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    F1 Race Strategy System                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Raw Race      │         │   HPC Compute   │         │   Enrichment    │
│   Telemetry     │────────▶│   Cluster       │────────▶│   Module        │
│                 │         │                 │         │  (port 8000)    │
└─────────────────┘         └─────────────────┘         └────────┬────────┘
                                                                  │
                                                                  │ POST webhook
                                                                  │ (enriched data)
                                                                  │
                                                                  ▼
                            ┌─────────────────────────────────────────────┐
                            │     AI Intelligence Layer (port 9000)       │
                            │  ┌─────────────────────────────────────┐   │
                            │  │  Step 1: Strategy Brainstorming      │   │
                            │  │  - Generate 20 diverse strategies    │   │
                            │  │  - Temperature: 0.9 (creative)       │   │
                            │  └─────────────────────────────────────┘   │
                            │                    │                        │
                            │                    ▼                        │
                            │  ┌─────────────────────────────────────┐   │
                            │  │  Step 2: Strategy Analysis           │   │
                            │  │  - Select top 3 strategies           │   │
                            │  │  - Temperature: 0.3 (analytical)     │   │
                            │  └─────────────────────────────────────┘   │
                            │                                             │
                            │  Powered by: Google Gemini 1.5 Pro          │
                            └──────────────────┬──────────────────────────┘
                                               │
                                               │ Strategic recommendations
                                               │
                                               ▼
                            ┌─────────────────────────────────────────┐
                            │      Race Engineers / Frontend          │
                            │  - Win probabilities                    │
                            │  - Risk assessments                     │
                            │  - Engineer briefs                      │
                            │  - Driver radio scripts                 │
                            │  - ECU commands                         │
                            └─────────────────────────────────────────┘
```

## Data Flow - Detailed

```
1. ENRICHED TELEMETRY INPUT
┌────────────────────────────────────────────────────────────────┐
│ {                                                               │
│   "lap": 27,                                                    │
│   "aero_efficiency": 0.83,        // 0-1, higher = better      │
│   "tire_degradation_index": 0.65, // 0-1, higher = worse       │
│   "ers_charge": 0.72,             // 0-1, energy available     │
│   "fuel_optimization_score": 0.91,// 0-1, efficiency           │
│   "driver_consistency": 0.89,     // 0-1, lap-to-lap variance  │
│   "weather_impact": "medium"      // low/medium/high           │
│ }                                                               │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
2. RACE CONTEXT INPUT
┌────────────────────────────────────────────────────────────────┐
│ {                                                               │
│   "race_info": {                                                │
│     "track_name": "Monaco",                                     │
│     "current_lap": 27,                                          │
│     "total_laps": 58                                            │
│   },                                                            │
│   "driver_state": {                                             │
│     "driver_name": "Hamilton",                                  │
│     "current_position": 4,                                      │
│     "current_tire_compound": "medium",                          │
│     "tire_age_laps": 14                                         │
│   },                                                            │
│   "competitors": [...]                                          │
│ }                                                               │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
3. TELEMETRY ANALYSIS
┌────────────────────────────────────────────────────────────────┐
│ • Calculate tire degradation rate: 0.030/lap                    │
│ • Project tire cliff: Lap 33                                    │
│ • Analyze ERS pattern: stable                                   │
│ • Assess fuel situation: OK                                     │
│ • Evaluate driver form: excellent                               │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
4. STEP 1: BRAINSTORM (Gemini AI)
┌────────────────────────────────────────────────────────────────┐
│ Temperature: 0.9 (high creativity)                              │
│ Prompt includes:                                                │
│   • Last 10 laps telemetry                                      │
│   • Calculated trends                                           │
│   • Race constraints                                            │
│   • Competitor analysis                                         │
│                                                                 │
│ Output: 20 diverse strategies                                   │
│   • Conservative (1-stop, low risk)                             │
│   • Standard (balanced approach)                                │
│   • Aggressive (undercut/overcut)                               │
│   • Reactive (respond to competitors)                           │
│   • Contingency (safety car, rain)                              │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
5. STRATEGY VALIDATION
┌────────────────────────────────────────────────────────────────┐
│ • Pit laps within valid range                                   │
│ • At least 2 tire compounds (F1 rule)                           │
│ • Stop count matches pit laps                                   │
│ • Tire sequence correct length                                  │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
6. STEP 2: ANALYZE (Gemini AI)
┌────────────────────────────────────────────────────────────────┐
│ Temperature: 0.3 (analytical consistency)                       │
│ Analysis framework:                                             │
│   1. Tire degradation projection                                │
│   2. Aero efficiency impact                                     │
│   3. Fuel management                                            │
│   4. Driver consistency                                         │
│   5. Weather & track position                                   │
│   6. Competitor analysis                                        │
│                                                                 │
│ Selection criteria:                                             │
│   • Rank 1: RECOMMENDED (highest podium %)                      │
│   • Rank 2: ALTERNATIVE (viable backup)                         │
│   • Rank 3: CONSERVATIVE (safest)                               │
└────────────────────────────────────────────────────────────────┘
                          │
                          ▼
7. FINAL OUTPUT
┌────────────────────────────────────────────────────────────────┐
│ For EACH of top 3 strategies:                                   │
│                                                                 │
│ • Predicted Outcome                                             │
│   - Finish position: P3                                         │
│   - P1 probability: 8%                                          │
│   - P2 probability: 22%                                         │
│   - P3 probability: 45%                                         │
│   - Confidence: 78%                                             │
│                                                                 │
│ • Risk Assessment                                               │
│   - Risk level: medium                                          │
│   - Key risks: ["Pit under 2.5s", "Traffic"]                   │
│   - Success factors: ["Tire advantage", "Window open"]          │
│                                                                 │
│ • Telemetry Insights                                            │
│   - "Tire cliff at lap 35"                                      │
│   - "Aero 0.83 - performing well"                               │
│   - "Fuel excellent, no saving"                                 │
│   - "Driver form excellent"                                     │
│                                                                 │
│ • Engineer Brief                                                │
│   - Title: "Aggressive Undercut Lap 28"                         │
│   - Summary: "67% chance P3 or better"                          │
│   - Key points: [...]                                           │
│   - Execution steps: [...]                                      │
│                                                                 │
│ • Driver Audio Script                                           │
│   "Box this lap. Softs going on. Push mode."                    │
│                                                                 │
│ • ECU Commands                                                  │
│   - Fuel: RICH                                                  │
│   - ERS: AGGRESSIVE_DEPLOY                                      │
│   - Engine: PUSH                                                │
│                                                                 │
│ • Situational Context                                           │
│   - "Decision needed in 2 laps"                                 │
│   - "Tire deg accelerating"                                     │
└────────────────────────────────────────────────────────────────┘
```

## API Endpoints Detail

```
┌─────────────────────────────────────────────────────────────────┐
│  GET /api/health                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Purpose: Health check                                           │
│  Response: {status, version, demo_mode}                          │
│  Latency: <100ms                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  POST /api/ingest/enriched                                       │
├─────────────────────────────────────────────────────────────────┤
│  Purpose: Webhook receiver from enrichment service               │
│  Input: Single lap enriched telemetry                            │
│  Action: Store in buffer (max 100 records)                       │
│  Response: {status, lap, buffer_size}                            │
│  Latency: <50ms                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  POST /api/strategy/brainstorm                                   │
├─────────────────────────────────────────────────────────────────┤
│  Purpose: Generate 20 diverse strategies                         │
│  Input:                                                          │
│    - enriched_telemetry (optional, auto-fetch if missing)        │
│    - race_context (required)                                     │
│  Process:                                                        │
│    1. Fetch telemetry if needed                                  │
│    2. Build prompt with telemetry analysis                       │
│    3. Call Gemini (temp=0.9)                                     │
│    4. Parse & validate strategies                                │
│  Output: {strategies: [20 strategies]}                           │
│  Latency: <5s (target)                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  POST /api/strategy/analyze                                      │
├─────────────────────────────────────────────────────────────────┤
│  Purpose: Analyze 20 strategies, select top 3                    │
│  Input:                                                          │
│    - enriched_telemetry (optional, auto-fetch if missing)        │
│    - race_context (required)                                     │
│    - strategies (required, typically 20)                         │
│  Process:                                                        │
│    1. Fetch telemetry if needed                                  │
│    2. Build analytical prompt                                    │
│    3. Call Gemini (temp=0.3)                                     │
│    4. Parse nested response structures                           │
│  Output:                                                         │
│    - top_strategies: [3 detailed strategies]                     │
│    - situational_context: {...}                                  │
│  Latency: <10s (target)                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Integration Patterns

### Pattern 1: Pull Model
```
Enrichment Service (8000)  ←─────GET /enriched─────  AI Layer (9000)
                                 [polls periodically]
```

### Pattern 2: Push Model (RECOMMENDED)
```
Enrichment Service (8000)  ─────POST /ingest/enriched────▶  AI Layer (9000)
                                [webhook on new data]
```

### Pattern 3: Direct Request
```
Client  ──POST /brainstorm──▶  AI Layer (9000)
        [includes telemetry]
```

## Error Handling Flow

```
Request
  │
  ▼
┌─────────────────┐
│ Validate Input  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     NO      ┌──────────────────┐
│ Telemetry       │────────────▶│ Fetch from       │
│ Provided?       │             │ localhost:8000   │
└────────┬────────┘             └────────┬─────────┘
    YES  │                               │
         └───────────────┬───────────────┘
                         ▼
                 ┌──────────────┐
                 │ Call Gemini  │
                 └──────┬───────┘
                        │
                   ┌────┴────┐
                   │ Success?│
                   └────┬────┘
                   YES  │  NO
                        │   │
                        │   ▼
                        │  ┌────────────────┐
                        │  │ Retry with     │
                        │  │ stricter prompt│
                        │  └────────┬───────┘
                        │           │
                        │      ┌────┴────┐
                        │      │Success? │
                        │      └────┬────┘
                        │      YES  │  NO
                        │           │   │
                        └───────────┤   │
                                    │   ▼
                                    │  ┌────────────┐
                                    │  │ Return     │
                                    │  │ Error 500  │
                                    │  └────────────┘
                                    ▼
                            ┌──────────────┐
                            │ Return       │
                            │ Success 200  │
                            └──────────────┘
```

## Performance Characteristics

| Component | Target | Typical | Max |
|-----------|--------|---------|-----|
| Health check | <100ms | 50ms | 200ms |
| Webhook ingest | <50ms | 20ms | 100ms |
| Brainstorm (20 strategies) | <5s | 3-4s | 10s |
| Analyze (top 3) | <10s | 6-8s | 20s |
| Gemini API call | <3s | 2s | 8s |
| Telemetry fetch | <500ms | 200ms | 1s |

## Scalability Considerations

- **Concurrent Requests**: FastAPI async handles multiple simultaneously
- **Rate Limiting**: Gemini API has quotas (check your tier)
- **Caching**: Demo mode caches identical requests
- **Buffer Size**: Webhook buffer limited to 100 records
- **Memory**: ~100MB per service instance

---

Built for the HPC + AI Race Strategy Hackathon 🏎️
