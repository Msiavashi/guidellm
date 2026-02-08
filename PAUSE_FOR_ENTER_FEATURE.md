# Pause for Enter Feature

## Overview

The `--pause-for-enter` flag allows you to pause execution before each benchmark run and wait for manual confirmation by pressing Enter. This is useful for manual inspection, server adjustments, or coordination between benchmark runs.

## Usage

### Basic Usage

```bash
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 1 --rate 8 --rate 16 \
  --pause-for-enter \
  --data "/path/to/data.json" \
  --max-seconds 60
```

### Combined with Delays

```bash
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 1 --rate 8 --rate 16 \
  --delay 0 --delay 10 --delay 30 \
  --pause-for-enter \
  --data "/path/to/data.json" \
  --max-seconds 60
```

**Execution Order:**
1. Delay (if specified)
2. **Pause and wait for Enter** ← Manual confirmation
3. Backend restart (if flag set)
4. Run benchmark

### Combined with Backend Restart

```bash
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 1 --rate 8 --rate 16 \
  --delay 0 --delay 10 --delay 30 \
  --restart-backend-between-runs \
  --pause-for-enter \
  --data "/path/to/data.json" \
  --max-seconds 60
```

**Full Execution Order:**
1. Delay (if specified)
2. **Pause and wait for Enter** ← Manual confirmation
3. Backend restart (if flag set) ← Automatic
4. Run benchmark

## Behavior

### What Happens

When `--pause-for-enter` is set:

1. **Before Each Run** (including the first):
   - Benchmark execution pauses
   - You see: `[INFO] Paused before benchmark (run N). Press Enter to continue...`
   - Execution waits for you to press Enter
   - You see: `[INFO] Continuing with benchmark...`
   - Benchmark proceeds

2. **Interactive Control**:
   - You can inspect server metrics
   - Adjust server configuration
   - Check resource usage
   - Coordinate with other systems
   - Press Enter when ready to proceed

### Example Session

```
[INFO] Delaying for 0 seconds before benchmark run 1...
[INFO] Paused before benchmark (run 1). Press Enter to continue...
← You press Enter
[INFO] Continuing with benchmark...
[INFO] Starting benchmark for rate 1...
... benchmark runs ...
[INFO] Benchmark 1 complete

[INFO] Delaying for 10 seconds before benchmark run 2...
[INFO] Paused before benchmark (run 2). Press Enter to continue...
← You check server metrics, then press Enter
[INFO] Continuing with benchmark...
[INFO] Restarting backend between benchmark runs...
[INFO] Backend restarted successfully
[INFO] Starting benchmark for rate 8...
... benchmark runs ...
```

## Use Cases

### 1. Manual Server Inspection

```bash
--pause-for-enter
```

**Scenario**: Check server metrics between runs
- Pause before each rate
- SSH into server to check logs/metrics
- Verify server is ready
- Press Enter to continue

### 2. Server Adjustment

```bash
--pause-for-enter
```

**Scenario**: Adjust server configuration between rates
- Pause before high-rate run
- Modify server settings (e.g., increase batch size)
- Restart server components if needed
- Press Enter when ready

### 3. Coordinated Testing

```bash
--pause-for-enter
```

**Scenario**: Coordinate with other test systems
- Pause before each run
- Start monitoring tools
- Trigger external logging
- Synchronize with team members
- Press Enter to proceed

### 4. Resource Verification

```bash
--pause-for-enter --restart-backend-between-runs
```

**Scenario**: Verify clean state between runs
- Pause after backend restart
- Check connection pool is fresh
- Verify memory has been cleared
- Confirm server resources available
- Press Enter to continue

### 5. Debugging Connection Issues

```bash
--pause-for-enter --restart-backend-between-runs --delay 30
```

**Scenario**: Debug TensorRT-LLM connection problems
- Wait 30 seconds for server recovery
- Pause to check server status
- Confirm no lingering connections
- Backend restarts to ensure fresh state
- Press Enter when server is ready

## Full Feature Integration

### Your Complete Command

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

### Execution Flow for Rate 8

```
Time: 0s
│
├─ Run 7 completes
│
├─ [1] Delay: 10 seconds
│    └─ Server recovery time
│
Time: 10s
│
├─ [2] Pause for Enter ⏸️
│    └─ "Paused before benchmark (run 8). Press Enter to continue..."
│    └─ You check: curl http://192.168.2.34:8000/health
│    └─ Server healthy ✅
│    └─ You press Enter
│
├─ [3] Backend Restart 🔄
│    └─ Shutdown: Close connections
│    └─ Startup: Open fresh connections
│    └─ Validate: Check backend ready
│
Time: ~12s
│
├─ [4] Run Benchmark 🚀
│    └─ Execute rate 8 benchmark
│    └─ Success! ✅
```

## Implementation Details

### Async-Safe Input

The implementation uses `asyncio.run_in_executor()` to avoid blocking:

```python
if pause_for_enter:
    logger.info("Paused before benchmark (run N). Press Enter to continue...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, input)  # Non-blocking
    logger.info("Continuing with benchmark...")
```

This ensures:
- Doesn't block the event loop
- Works in async context
- Maintains responsive behavior

### Order of Operations

The execution order ensures optimal workflow:

1. **Delay first**: Give server time to recover automatically
2. **Pause second**: Manual check after server has recovered
3. **Restart third**: Clean connections after manual verification
4. **Benchmark fourth**: Execute with fresh, verified state

## Backward Compatibility

✅ **Fully backward compatible**
- Default: `False` (no pausing)
- Only pauses when explicitly set
- Existing workflows unchanged
- Can be combined with all other flags

## When to Use

### ✅ Use `--pause-for-enter` when:

- Need manual verification between runs
- Coordinating with external systems
- Debugging connection or server issues
- Want control over timing
- Adjusting server configuration between runs
- Learning/understanding server behavior

### ❌ Don't use when:

- Running automated/unattended benchmarks
- CI/CD pipelines (no interactive terminal)
- Quick iterations needed
- Already confident in server stability
- Running hundreds of benchmark rates

## Tips

### 1. Quick Server Health Check

While paused, run:
```bash
# In another terminal
curl http://192.168.2.34:8000/health
curl http://192.168.2.34:8000/v1/models
nvidia-smi  # Check GPU usage
```

### 2. Monitor Server Logs

While paused:
```bash
# In another terminal
tail -f /var/log/trtllm-server.log
```

### 3. Adjust Rate Strategy

If a rate fails:
- Note which rate caused issues
- Cancel current run (Ctrl+C)
- Adjust delays for that rate
- Restart with updated delays

### 4. Resource Cleanup

While paused:
```bash
# Check and clear if needed
docker stats  # Container resource usage
free -h       # Memory availability
```

## Log Messages

### Start Message
```
[INFO] Paused before benchmark (run N). Press Enter to continue...
```

### Continue Message
```
[INFO] Continuing with benchmark...
```

### Combined with Other Features
```
[INFO] Delaying for 10 seconds before benchmark run 8...
[INFO] Paused before benchmark (run 8). Press Enter to continue...
[INFO] Continuing with benchmark...
[INFO] Restarting backend between benchmark runs...
[INFO] Backend restarted successfully
```

## Summary

| Aspect | Details |
|--------|---------|
| **Flag** | `--pause-for-enter` |
| **Type** | Boolean flag (no value needed) |
| **Default** | `False` (no pausing) |
| **When** | Before each benchmark run (including first) |
| **Action** | Waits for Enter key press |
| **Use Case** | Manual inspection, coordination, debugging |
| **Combines with** | `--delay`, `--restart-backend-between-runs` |
| **Order** | Delay → Pause → Restart → Benchmark |

**Perfect for**: Interactive debugging and manual control over benchmark execution!
