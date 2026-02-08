# Quick Reference: Your TensorRT-LLM Benchmark Commands

## Automated Execution (Recommended for Production)

```bash
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --request-type text_completions \
  --profile poisson \
  --rate 1 --rate 2 --rate 3 --rate 4 --rate 5 --rate 6 --rate 7 \
  --rate 8 --rate 9 --rate 12 --rate 16 --rate 24 --rate 32 \
  --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 \
  --delay 10 --delay 15 --delay 20 --delay 30 --delay 45 --delay 60 \
  --restart-backend-between-runs \
  --data "/home/siavashi/mohamamd/tests/axon-paper-experiments/ShareGPT_V3_unfiltered_cleaned_split.json" \
  --processor meta-llama/Meta-Llama-3-8B \
  --sharegpt-format conversational \
  --compute-output-tokens-from-response \
  --token-budget-total 2047 \
  --input-length-stats \
  --max-seconds 60 \
  --use-filter-cache
```

**Features**:
- ⏱️ Per-rate delays for server recovery
- 🔄 Backend restart for fresh connections
- 🤖 Fully automated (no manual intervention)

## Manual Control (For Debugging/Inspection)

```bash
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --request-type text_completions \
  --profile poisson \
  --rate 1 --rate 2 --rate 3 --rate 4 --rate 5 --rate 6 --rate 7 \
  --rate 8 --rate 9 --rate 12 --rate 16 --rate 24 --rate 32 \
  --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 \
  --delay 10 --delay 15 --delay 20 --delay 30 --delay 45 --delay 60 \
  --restart-backend-between-runs \
  --pause-for-enter \
  --data "/home/siavashi/mohamamd/tests/axon-paper-experiments/ShareGPT_V3_unfiltered_cleaned_split.json" \
  --processor meta-llama/Meta-Llama-3-8B \
  --sharegpt-format conversational \
  --compute-output-tokens-from-response \
  --token-budget-total 2047 \
  --input-length-stats \
  --max-seconds 60 \
  --use-filter-cache
```

**Features**:
- ⏱️ Per-rate delays for server recovery
- 🔄 Backend restart for fresh connections
- ⏸️ **Manual pause** before each rate for inspection
- 👤 Interactive control over execution

**What happens**:
1. Waits for specified delay
2. **Pauses and shows**: "Press Enter to continue..."
3. You inspect server, press Enter when ready
4. Backend restarts with fresh connections
5. Benchmark runs

## Execution Timeline (Automated)

| Benchmark | Rate | Delay Before | Backend Action | Max Duration | Status |
|-----------|------|--------------|----------------|--------------|---------|
| Run 1     | 1    | 0s           | *(first run)*  | 60s          | ✓ Ready |
| Run 2     | 2    | 0s           | 🔄 Restart     | 60s          | ✓ Fresh |
| Run 3     | 3    | 0s           | 🔄 Restart     | 60s          | ✓ Fresh |
| Run 4     | 4    | 0s           | 🔄 Restart     | 60s          | ✓ Fresh |
| Run 5     | 5    | 0s           | 🔄 Restart     | 60s          | ✓ Fresh |
| Run 6     | 6    | 0s           | 🔄 Restart     | 60s          | ✓ Fresh |
| Run 7     | 7    | 0s           | 🔄 Restart     | 60s          | ✓ Fresh |
| Run 8     | 8    | 10s ⏱️       | 🔄 Restart     | 60s          | 💚 Recovery |
| Run 9     | 9    | 15s ⏱️       | 🔄 Restart     | 60s          | 💚 Recovery |
| Run 10    | 12   | 20s ⏱️       | 🔄 Restart     | 60s          | 💚 Recovery |
| Run 11    | 16   | 30s ⏱️       | 🔄 Restart     | 60s          | 💚 Recovery |
| Run 12    | 24   | 45s ⏱️       | 🔄 Restart     | 60s          | 💚 Recovery |
| Run 13    | 32   | 60s ⏱️       | 🔄 Restart     | 60s          | 💚 Recovery |

## Execution Timeline (Manual Control)

| Benchmark | Rate | Delay | Pause ⏸️ | Backend | Status |
|-----------|------|-------|---------|---------|---------|
| Run 1     | 1    | 0s    | **Press Enter** | *(first)* | 👤 Manual |
| Run 2     | 2    | 0s    | **Press Enter** | 🔄 Restart | 👤 Manual |
| Run 3     | 3    | 0s    | **Press Enter** | 🔄 Restart | 👤 Manual |
| Run 8     | 8    | 10s   | **Press Enter** | 🔄 Restart | 👤 Manual |
| Run 13    | 32   | 60s   | **Press Enter** | 🔄 Restart | 👤 Manual |

## Estimated Runtime

### Automated
- **Benchmarking**: Up to 13 × 60s = 780s (~13 min)
- **Delays**: 180s (3 min)
- **Backend Restarts**: 24s (~30 sec)
- **Total**: ~16.5 minutes

### Manual Control
- **Same as automated** + your inspection time
- Plan for ~20-25 minutes with careful inspection

## What to Check During Pause ⏸️

When paused, you can:

### 1. Check Server Health
```bash
curl http://192.168.2.34:8000/health
curl http://192.168.2.34:8000/v1/models
```

### 2. Monitor Resources
```bash
nvidia-smi          # GPU usage
free -h             # Memory
docker stats        # Container resources
```

### 3. Check Server Logs
```bash
tail -f /var/log/trtllm-server.log
```

### 4. Verify Clean State
```bash
netstat -an | grep 8000  # Check connections
ps aux | grep trtllm     # Check processes
```

## Feature Combinations

### Option 1: Just Delays (Basic)
```bash
--delay 0 --delay 10 --delay 30
```
Automatic spacing, same connections

### Option 2: Delays + Backend Restart (Recommended)
```bash
--delay 0 --delay 10 --delay 30 \
--restart-backend-between-runs
```
Automatic spacing + fresh connections

### Option 3: All Features (Maximum Control)
```bash
--delay 0 --delay 10 --delay 30 \
--restart-backend-between-runs \
--pause-for-enter
```
Automatic + fresh connections + manual verification

## Troubleshooting

### If Still Getting Errors

1. **Try manual control first**:
   ```bash
   --pause-for-enter
   ```
   Inspect server at each pause

2. **Increase delays**:
   ```bash
   --delay 20 --delay 40 --delay 60
   ```

3. **Check logs during pause**:
   ```bash
   tail -f server.log
   ```
   Look for errors before pressing Enter

4. **Verify backend restart**:
   ```bash
   grep "Backend restarted successfully" output.log
   ```
   Should see 12 messages for 13 rates

## Quick Decision Guide

**Choose Automated** if:
- ✅ Server is stable
- ✅ Running in CI/CD
- ✅ Unattended execution needed
- ✅ Already tested manually

**Choose Manual Control** if:
- ✅ First time testing these rates
- ✅ Debugging connection issues
- ✅ Want to verify each step
- ✅ Need to adjust server between runs
- ✅ Learning server behavior

## Summary

| Aspect | Automated | Manual Control |
|--------|-----------|----------------|
| **Delays** | ✅ Yes | ✅ Yes |
| **Backend Restart** | ✅ Yes | ✅ Yes |
| **Manual Pause** | ❌ No | ✅ Yes |
| **Runtime** | ~16.5 min | ~20-25 min |
| **Use Case** | Production | Debugging |
| **Reliability** | High | Highest |
| **Control** | Automatic | Complete |

---

**🚀 Ready to benchmark reliably!**
