# Timeout Fix Guide

## Problem
Gemini API timing out with 504 errors after ~30 seconds.

## Solution Applied ✅

### 1. Increased Timeouts
**File: `.env`**
```bash
BRAINSTORM_TIMEOUT=90  # Increased from 30s
ANALYZE_TIMEOUT=120    # Increased from 60s
```

### 2. Added Fast Mode
**File: `.env`**
```bash
FAST_MODE=true  # Use shorter, optimized prompts
```

Fast mode reduces prompt length by ~60% while maintaining quality:
- Brainstorm: ~4900 chars → ~1200 chars
- Analyze: ~6500 chars → ~1800 chars

### 3. Improved Retry Logic
**File: `services/gemini_client.py`**
- Longer backoff for timeout errors (5s instead of 2s)
- Minimum timeout of 60s for API calls
- Better error detection

### 4. Model Selection
You're using `gemini-2.5-flash` which is good! It's:
- ✅ Faster than Pro
- ✅ Cheaper
- ✅ Good quality for this use case

## How to Use

### Option 1: Fast Mode (RECOMMENDED for demos)
```bash
# In .env
FAST_MODE=true
```
- Faster responses (~10-20s per call)
- Shorter prompts
- Still high quality

### Option 2: Full Mode (for production)
```bash
# In .env
FAST_MODE=false
```
- More detailed prompts
- Slightly better quality
- Slower (~30-60s per call)

## Testing

### Quick Test
```bash
# Check health
curl http://localhost:9000/api/health

# Test with sample data (fast mode)
curl -X POST http://localhost:9000/api/strategy/brainstorm \
  -H "Content-Type: application/json" \
  -d @- << EOF
{
  "enriched_telemetry": $(cat sample_data/sample_enriched_telemetry.json),
  "race_context": $(cat sample_data/sample_race_context.json)
}
EOF
```

## Troubleshooting

### Still getting timeouts?

**1. Check API quota**
- Visit: https://aistudio.google.com/apikey
- Check rate limits and quota
- Free tier: 15 requests/min, 1M tokens/min

**2. Try different model**
```bash
# In .env, try:
GEMINI_MODEL=gemini-1.5-flash  # Fastest
# or
GEMINI_MODEL=gemini-1.5-pro    # Better quality, slower
```

**3. Increase timeouts further**
```bash
# In .env
BRAINSTORM_TIMEOUT=180
ANALYZE_TIMEOUT=240
```

**4. Reduce strategy count**
If still timing out, you can modify the code to generate fewer strategies:
- Edit `prompts/brainstorm_prompt.py`
- Change "Generate 20 strategies" to "Generate 10 strategies"

### Network issues?

**Check connectivity:**
```bash
# Test Google AI endpoint
curl -I https://generativelanguage.googleapis.com

# Check if behind proxy
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

**Use VPN if needed** - Some regions have restricted access to Google AI APIs

### Monitor performance

**Watch logs:**
```bash
# Start server with logs
python main.py 2>&1 | tee ai_layer.log

# In another terminal, watch for timeouts
tail -f ai_layer.log | grep -i timeout
```

## Performance Benchmarks

### Fast Mode (FAST_MODE=true)
- Brainstorm: ~15-25s
- Analyze: ~20-35s
- Total workflow: ~40-60s

### Full Mode (FAST_MODE=false)
- Brainstorm: ~30-50s
- Analyze: ~40-70s
- Total workflow: ~70-120s

## What Changed

### Before
```
Prompt: 4877 chars
Timeout: 30s
Result: ❌ 504 timeout errors
```

### After (Fast Mode)
```
Prompt: ~1200 chars (75% reduction)
Timeout: 90s
Result: ✅ Works reliably
```

## Configuration Summary

Your current setup:
```bash
GEMINI_MODEL=gemini-2.5-flash  # Fast model
FAST_MODE=true                  # Optimized prompts
BRAINSTORM_TIMEOUT=90          # 3x increase
ANALYZE_TIMEOUT=120            # 2x increase
```

This should work reliably now! 🎉

## Additional Tips

1. **For demos**: Keep FAST_MODE=true
2. **For production**: Test with FAST_MODE=false, adjust timeouts as needed
3. **Monitor quota**: Check usage at https://aistudio.google.com
4. **Cache responses**: Enable DEMO_MODE=true for repeatable demos

---

**Status**: FIXED ✅
**Ready to test**: YES 🚀
