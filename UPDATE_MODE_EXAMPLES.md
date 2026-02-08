# Update Mode Practical Examples

## Real-World Scenarios

### Scenario 1: Re-Running Failed Rate

Your full sweep had one failed rate. Fix and update it without re-running everything.

```bash
# Initial sweep - rate 16 fails due to server issue
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 1 --rate 2 --rate 4 --rate 8 --rate 16 --rate 32 \
  --output-dir ./my-sweep \
  --restart-backend-between-runs

# Output: benchmarks.json has 6 benchmarks, but rate 16 has errors

# Fix server issue, then re-run ONLY rate 16
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 16 \
  --delay 30 \
  --output-dir ./my-sweep \
  --restart-backend-between-runs \
  --update

# Result: benchmarks.json updated with fresh rate 16 data
#         Rates 1,2,4,8,32 preserved unchanged
```

### Scenario 2: Incremental Sweep Building

Build a comprehensive sweep over multiple sessions.

```bash
# Monday: Test low rates
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 1 --rate 2 --rate 3 \
  --output-dir ./weekly-sweep \
  --restart-backend-between-runs

# Tuesday: Add medium rates
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 4 --rate 6 --rate 8 \
  --delay 10 --delay 15 --delay 20 \
  --output-dir ./weekly-sweep \
  --restart-backend-between-runs \
  --update

# Wednesday: Add high rates
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 12 --rate 16 --rate 24 --rate 32 \
  --delay 20 --delay 30 --delay 45 --delay 60 \
  --output-dir ./weekly-sweep \
  --restart-backend-between-runs \
  --update

# Result: Single benchmarks.json with all 11 rates
```

### Scenario 3: Configuration Optimization

Test different configurations for a specific rate.

```bash
# Initial run with default settings
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 1 --rate 8 --rate 16 \
  --max-seconds 60 \
  --output-dir ./config-test

# Rate 16 shows high error rate, try with longer duration
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 16 \
  --max-seconds 120 \
  --delay 60 \
  --output-dir ./config-test \
  --restart-backend-between-runs \
  --update

# Still issues? Try with pause for manual inspection
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 16 \
  --max-seconds 120 \
  --delay 90 \
  --output-dir ./config-test \
  --restart-backend-between-runs \
  --pause-for-enter \
  --update

# Result: Rate 16 updated with optimized configuration
#         Rates 1 and 8 preserved from initial run
```

### Scenario 4: Your TensorRT-LLM Full Workflow

Complete workflow for building and refining a comprehensive sweep.

```bash
# Step 1: Initial full sweep
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
  --use-filter-cache \
  --output-dir ./trtllm-sweep

# Step 2: Rates 24 and 32 had errors, re-run with more delay and manual control
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --request-type text_completions \
  --profile poisson \
  --rate 24 --rate 32 \
  --delay 90 --delay 120 \
  --restart-backend-between-runs \
  --pause-for-enter \
  --data "/home/siavashi/mohamamd/tests/axon-paper-experiments/ShareGPT_V3_unfiltered_cleaned_split.json" \
  --processor meta-llama/Meta-Llama-3-8B \
  --sharegpt-format conversational \
  --compute-output-tokens-from-response \
  --token-budget-total 2047 \
  --max-seconds 90 \
  --use-filter-cache \
  --output-dir ./trtllm-sweep \
  --update

# Result: benchmarks.json with all 13 rates
#         Rates 24 and 32 have updated results with optimized settings
#         Rates 1-16 preserved from initial run
```

## Before/After Comparison

### Scenario: Re-running Rate 5

**Initial Run:**
```bash
guidellm benchmark run \
  --rate 1 --rate 2 --rate 5 --rate 10 \
  --output-dir ./test \
  --max-seconds 30
```

**Result:** `./test/benchmarks.json`
```json
{
  "benchmarks": [
    {"config": {"strategy": {"type_": "constant", "rate": 1.0}}, ...},
    {"config": {"strategy": {"type_": "constant", "rate": 2.0}}, ...},
    {"config": {"strategy": {"type_": "constant", "rate": 5.0}}, ...},  ← 30s duration
    {"config": {"strategy": {"type_": "constant", "rate": 10.0}}, ...}
  ]
}
```

**WITHOUT `--update` (Default):**
```bash
guidellm benchmark run \
  --rate 5 \
  --output-dir ./test \
  --max-seconds 60  # More time
```

**Result:** `./test/benchmarks.json` **OVERWRITTEN**
```json
{
  "benchmarks": [
    {"config": {"strategy": {"type_": "constant", "rate": 5.0}}, ...}  ← 60s duration
  ]
}
```
❌ **Rates 1, 2, and 10 are LOST!**

**WITH `--update`:**
```bash
guidellm benchmark run \
  --rate 5 \
  --output-dir ./test \
  --max-seconds 60 \
  --update  # ← Key difference
```

**Result:** `./test/benchmarks.json` **MERGED**
```json
{
  "benchmarks": [
    {"config": {"strategy": {"type_": "constant", "rate": 1.0}}, ...},  ← Preserved
    {"config": {"strategy": {"type_": "constant", "rate": 2.0}}, ...},  ← Preserved
    {"config": {"strategy": {"type_": "constant", "rate": 5.0}}, ...},  ← Updated (60s)
    {"config": {"strategy": {"type_": "constant", "rate": 10.0}}, ...}  ← Preserved
  ]
}
```
✅ **All rates preserved, rate 5 updated!**

## Common Workflows

### Workflow 1: Quick Fix

```bash
# 1. Run full sweep
guidellm benchmark run --rate 1 --rate 2 --rate 5 --rate 10 --output-dir ./sweep

# 2. Notice rate 5 had issues

# 3. Fix and update
guidellm benchmark run --rate 5 --output-dir ./sweep --update

# Done! All rates intact, rate 5 fixed
```

### Workflow 2: Gradual Expansion

```bash
# 1. Start conservative
guidellm benchmark run --rate 1 --rate 2 --output-dir ./sweep

# 2. Add more rates
guidellm benchmark run --rate 4 --rate 8 --output-dir ./sweep --update

# 3. Add high rates
guidellm benchmark run --rate 16 --rate 32 --output-dir ./sweep --update

# Done! Complete sweep built incrementally
```

### Workflow 3: A/B Testing

```bash
# 1. Test rate 10 with config A
guidellm benchmark run --rate 10 --max-seconds 30 --output-dir ./ab-test

# 2. Load other rates
guidellm benchmark run --rate 5 --rate 15 --output-dir ./ab-test --update

# 3. Re-test rate 10 with config B
guidellm benchmark run --rate 10 --max-seconds 60 --output-dir ./ab-test --update

# Done! Rate 10 has config B results, rates 5 and 15 preserved
```

## Tips and Best Practices

### 1. Always Use Same Output Directory

```bash
# ✅ Good - consistent directory
--output-dir ./my-sweep
--output-dir ./my-sweep --update

# ❌ Bad - different directories
--output-dir ./sweep1
--output-dir ./sweep2 --update  # Won't find original file!
```

### 2. Match Profile Type

```bash
# ✅ Good - same profile
--profile poisson --rate 5          # Initial
--profile poisson --rate 5 --update # Update

# ⚠️ Different - creates separate entry
--profile constant --rate 5          # Initial (constant@5.0)
--profile poisson --rate 5 --update  # New entry (poisson@5.0)
```

### 3. Verify Before Committing

```bash
# Test update in separate directory first
guidellm benchmark run --rate 5 --output-dir ./test-update --update

# Verify results look good
cat ./test-update/benchmarks.json

# Then update production
guidellm benchmark run --rate 5 --output-dir ./production --update
```

### 4. Backup Important Results

```bash
# Before updating production data
cp ./production/benchmarks.json ./production/benchmarks.backup.json

# Then update safely
guidellm benchmark run --rate 5 --output-dir ./production --update
```

## Output File Behavior

### JSON Output (benchmarks.json)

✅ **Supports update mode**
- Existing file is loaded
- Benchmarks are merged
- Updated file is saved

### CSV, HTML Outputs

✅ **Regenerated from merged data**
- Not loaded or merged
- Completely regenerated from merged benchmarks
- Always reflect the complete merged dataset

## Edge Cases

### Different Strategy Types

```bash
# Run 1: Constant strategy
--profile constant --rate 5

# Run 2: Poisson strategy (different type)
--profile poisson --rate 5 --update

# Result: Both benchmarks exist (different keys)
# - constant@5.0
# - poisson@5.0
```

### Concurrent Strategy

```bash
# Run 1: Concurrent with 10 streams
--profile concurrent --rate 10

# Run 2: Update concurrent
--profile concurrent --rate 10 --update

# Matches by (concurrent, streams=10)
```

### No Existing File

```bash
# First time in directory
guidellm benchmark run --rate 5 --output-dir ./new-dir --update

# Behavior: Creates new file (same as without --update)
# Warning: "Could not load existing report... Creating new report."
```

## Verification

### Check What Changed

```bash
# Before update
cat ./results/benchmarks.json | jq '.benchmarks | length'
# Output: 5

# Run update
guidellm benchmark run --rate 3 --output-dir ./results --update

# After update
cat ./results/benchmarks.json | jq '.benchmarks | length'
# Output: 5 (same count, but rate 3 updated)

# Check rates
cat ./results/benchmarks.json | jq '.benchmarks[].config.strategy.rate'
# Output: 1, 2, 3, 8, 16 (all present)
```

### Verify Specific Rate

```bash
# Check rate 5 details
cat ./results/benchmarks.json | jq '.benchmarks[] | select(.config.strategy.rate == 5.0)'
```

## Summary Table

| Action | Command | Result |
|--------|---------|--------|
| **Initial sweep** | `--rate 1 --rate 2 --rate 3` | Creates benchmarks.json with 3 benchmarks |
| **Overwrite (default)** | `--rate 2` | benchmarks.json has ONLY rate 2 (❌ lost 1,3) |
| **Update** | `--rate 2 --update` | benchmarks.json has rates 1,2,3 (✅ rate 2 updated) |
| **Add new** | `--rate 4 --update` | benchmarks.json has rates 1,2,3,4 (✅ rate 4 added) |
| **Update multiple** | `--rate 1 --rate 3 --update` | benchmarks.json has 1,2,3 (✅ rates 1,3 updated) |

## Recommended Workflows

### For Production: Iterative Refinement

```bash
#!/bin/bash
# production-sweep.sh

OUTPUT_DIR="./production-sweep"

# Phase 1: Initial sweep with low/medium rates
guidellm benchmark run \
  --rate 1 --rate 2 --rate 4 --rate 8 \
  --output-dir $OUTPUT_DIR \
  --restart-backend-between-runs

# Phase 2: Add high rates with conservative settings
guidellm benchmark run \
  --rate 16 --rate 24 --rate 32 \
  --delay 30 --delay 60 --delay 90 \
  --output-dir $OUTPUT_DIR \
  --restart-backend-between-runs \
  --update

# Phase 3: If any rate failed, re-run with pause
# (Uncomment and set FAILED_RATE as needed)
# FAILED_RATE=24
# guidellm benchmark run \
#   --rate $FAILED_RATE \
#   --delay 90 \
#   --output-dir $OUTPUT_DIR \
#   --restart-backend-between-runs \
#   --pause-for-enter \
#   --update
```

### For Development: Quick Iterations

```bash
#!/bin/bash
# dev-iterate.sh

# Test one rate quickly
guidellm benchmark run --rate 5 --max-requests 20 --output-dir ./dev

# Iterate on that rate with different settings
for delay in 0 10 30; do
    echo "Testing rate 5 with ${delay}s delay"
    guidellm benchmark run \
        --rate 5 \
        --delay $delay \
        --max-requests 20 \
        --output-dir ./dev \
        --update
    sleep 2
done

# Result: Latest iteration saved for rate 5
```

## Integration with Other Features

### With Backend Restart

```bash
# Recommended: Update + restart for reliable results
guidellm benchmark run \
  --rate 16 \
  --output-dir ./results \
  --restart-backend-between-runs \
  --update
```

### With Per-Rate Delays

```bash
# Update multiple rates with delays
guidellm benchmark run \
  --rate 8 --rate 16 --rate 32 \
  --delay 10 --delay 30 --delay 60 \
  --output-dir ./results \
  --restart-backend-between-runs \
  --update
```

### With Pause for Enter

```bash
# Update with manual verification
guidellm benchmark run \
  --rate 32 \
  --delay 60 \
  --output-dir ./results \
  --restart-backend-between-runs \
  --pause-for-enter \
  --update
```

### All Features Combined

```bash
# Maximum control for critical rate
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 32 \
  --delay 90 \
  --restart-backend-between-runs \
  --pause-for-enter \
  --update \
  --data "/path/to/data.json" \
  --max-seconds 120 \
  --output-dir ./production-sweep
```

## Quick Reference Commands

### Fix One Failed Rate
```bash
guidellm benchmark run --rate <FAILED_RATE> --output-dir <DIR> --update
```

### Add New Rates
```bash
guidellm benchmark run --rate <NEW_RATE1> --rate <NEW_RATE2> --output-dir <DIR> --update
```

### Re-run Multiple Rates
```bash
guidellm benchmark run --rate <RATE1> --rate <RATE2> --output-dir <DIR> --update
```

### Update with Better Config
```bash
guidellm benchmark run --rate <RATE> --max-seconds <MORE_TIME> --output-dir <DIR> --update
```

---

**Perfect for**: Iterative benchmark refinement without losing previous results! 🎯
