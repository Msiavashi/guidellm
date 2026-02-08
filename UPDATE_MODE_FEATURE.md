# Update Mode Feature (`--update`)

## Overview

The `--update` flag allows you to update existing benchmark results instead of overwriting them completely. This is particularly useful when you want to re-run specific rates in a sweep without losing results from other rates.

## Problem Solved

### Without `--update` (Default Behavior)

```bash
# Run 1: Test rates 1, 2, 3
guidellm benchmark run --rate 1 --rate 2 --rate 3 --output-dir ./results

# Results: benchmarks.json contains results for rates 1, 2, 3

# Run 2: Re-test only rate 2
guidellm benchmark run --rate 2 --output-dir ./results

# Problem: benchmarks.json is OVERWRITTEN, only contains rate 2
# Results for rates 1 and 3 are LOST ❌
```

### With `--update` (New Behavior)

```bash
# Run 1: Test rates 1, 2, 3
guidellm benchmark run --rate 1 --rate 2 --rate 3 --output-dir ./results

# Results: benchmarks.json contains results for rates 1, 2, 3

# Run 2: Re-test only rate 2 with update mode
guidellm benchmark run --rate 2 --output-dir ./results --update

# Success: benchmarks.json contains updated rate 2 plus original rates 1 and 3
# Results for rates 1 and 3 are PRESERVED ✅
```

## Usage

### Basic Update

```bash
# Initial sweep
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 1 --rate 2 --rate 3 --rate 4 --rate 5 \
  --output-dir ./experiment1

# Re-run specific rate
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 3 \
  --output-dir ./experiment1 \
  --update
```

### Update Multiple Rates

```bash
# Initial sweep
guidellm benchmark run \
  --rate 1 --rate 2 --rate 3 --rate 4 --rate 5 \
  --output-dir ./results

# Re-run rates 2 and 4
guidellm benchmark run \
  --rate 2 --rate 4 \
  --output-dir ./results \
  --update
```

### Add New Rates to Existing Sweep

```bash
# Initial sweep (low rates)
guidellm benchmark run \
  --rate 1 --rate 2 --rate 3 \
  --output-dir ./results

# Add high rates later
guidellm benchmark run \
  --rate 8 --rate 16 --rate 32 \
  --output-dir ./results \
  --update

# Result: benchmarks.json contains rates 1, 2, 3, 8, 16, 32
```

## How It Works

### Matching Logic

Benchmarks are matched by their **strategy type** and **rate** (or **streams** for concurrent):

1. **Async Strategies** (constant, poisson):
   - Match by `(strategy_type, rate)`
   - Example: `(constant, 5.0)` matches `(constant, 5.0)`

2. **Concurrent Strategy**:
   - Match by `(strategy_type, streams)`
   - Example: `(concurrent, 10)` matches `(concurrent, 10)`

3. **Other Strategies** (synchronous, throughput, bursty):
   - Match by `strategy_type` only
   - Example: `(synchronous, None)` matches `(synchronous, None)`

### Update Process

```
1. Load existing benchmarks.json from output directory
   ↓
2. Run new benchmarks
   ↓
3. For each new benchmark:
   - Find matching benchmark in existing report (by strategy + rate)
   - If match found: REPLACE with new benchmark
   - If no match: ADD as new benchmark
   ↓
4. Keep all existing benchmarks that weren't updated
   ↓
5. Save merged report
```

## Examples

### Example 1: Fixing a Failed Rate

```bash
# Initial run - rate 8 fails due to server issue
guidellm benchmark run \
  --rate 1 --rate 2 --rate 4 --rate 8 --rate 16 \
  --output-dir ./sweep1

# Rate 8 had errors, fix server and re-run just that rate
guidellm benchmark run \
  --rate 8 \
  --output-dir ./sweep1 \
  --update

# Result: Fresh results for rate 8, original results for 1,2,4,16 preserved
```

### Example 2: Different Configurations

```bash
# Initial run with 60s max time
guidellm benchmark run \
  --rate 1 --rate 2 --rate 3 \
  --max-seconds 60 \
  --output-dir ./results

# Re-run rate 2 with longer duration for more data
guidellm benchmark run \
  --rate 2 \
  --max-seconds 120 \
  --output-dir ./results \
  --update

# Result: Rate 2 updated with 120s results, rates 1 and 3 still have 60s results
```

### Example 3: Iterative Sweep Building

```bash
# Day 1: Test low rates
guidellm benchmark run \
  --rate 1 --rate 2 --rate 3 \
  --output-dir ./weekly-sweep

# Day 2: Add medium rates
guidellm benchmark run \
  --rate 4 --rate 8 --rate 12 \
  --output-dir ./weekly-sweep \
  --update

# Day 3: Add high rates
guidellm benchmark run \
  --rate 16 --rate 24 --rate 32 \
  --output-dir ./weekly-sweep \
  --update

# Result: Single benchmarks.json with all rates from all days
```

## Output Messages

### When Loading Existing Report

```
[INFO] Loaded existing report with 5 benchmark(s)
```

### When Update Completes

```
[SUCCESS] Updated 2 existing benchmark(s), added 1 new benchmark(s)
           Total benchmarks in report: 6
```

### When No Existing Report Found

```
[WARNING] Could not load existing report: [Errno 2] No such file or directory: 'benchmarks.json'. Creating new report.
```

## Use Cases

### 1. Failed Benchmark Recovery

**Scenario**: One rate in your sweep failed due to temporary server issue

```bash
# Fix the failed rate without re-running successful ones
guidellm benchmark run --rate 8 --output-dir ./results --update
```

### 2. Incremental Sweep Expansion

**Scenario**: Start with low rates, add high rates later

```bash
# Phase 1: Low rates
guidellm benchmark run --rate 1 --rate 2 --rate 3 --output-dir ./sweep

# Phase 2: Add high rates
guidellm benchmark run --rate 16 --rate 32 --output-dir ./sweep --update
```

### 3. Configuration Refinement

**Scenario**: Update specific rates with better parameters

```bash
# Re-run problematic rate with more time
guidellm benchmark run --rate 16 --max-seconds 120 --output-dir ./sweep --update
```

### 4. Data Collection Over Time

**Scenario**: Build comprehensive dataset incrementally

```bash
# Collect data piece by piece, updating existing report
guidellm benchmark run --rate 5 --output-dir ./dataset --update  # Monday
guidellm benchmark run --rate 10 --output-dir ./dataset --update # Tuesday
guidellm benchmark run --rate 15 --output-dir ./dataset --update # Wednesday
```

### 5. A/B Testing Different Configurations

**Scenario**: Test same rate with different backend settings

```bash
# Test rate 10 with config A
guidellm benchmark run --rate 10 --backend-kwargs '{"timeout":30}' --output-dir ./test

# Update with config B
guidellm benchmark run --rate 10 --backend-kwargs '{"timeout":60}' --output-dir ./test --update
```

## Important Notes

### ⚠️ Matching is by Strategy and Rate

Benchmarks are matched by strategy type and rate/streams:
- `--rate 5` with `--profile constant` matches previous `constant@5.0`
- `--rate 5` with `--profile poisson` matches previous `poisson@5.0`
- Different profiles create different matches!

### ⚠️ Only Applies to JSON Output

Update mode only affects `benchmarks.json` (the serialized report). Other outputs (CSV, HTML) are regenerated from the complete merged report.

### ⚠️ Metadata is Updated

The merged report uses the **new** metadata (guidellm version, timestamp, etc.), not the old one.

### ⚠️ Args are Updated

The merged report uses the **new** args (configuration), which may differ from the original sweep args.

## Comparison with Default Behavior

| Aspect | Default (No --update) | With --update |
|--------|----------------------|---------------|
| **Existing File** | Overwritten completely | Loaded and merged |
| **Matching Benchmarks** | Lost | Replaced with new |
| **Non-matching Benchmarks** | Lost | Preserved |
| **New Benchmarks** | Saved | Added to existing |
| **Metadata** | From current run | From current run |
| **Use Case** | Complete fresh run | Incremental updates |

## Workflow Example

### Full Workflow: Iterative Sweep with Updates

```bash
# Step 1: Initial sweep of low/medium rates
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 1 --rate 2 --rate 4 --rate 8 \
  --max-seconds 60 \
  --output-dir ./production-sweep \
  --restart-backend-between-runs

# Results: benchmarks.json with 4 benchmarks

# Step 2: Rate 8 showed errors, re-run with more delay
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 8 \
  --delay 30 \
  --max-seconds 60 \
  --output-dir ./production-sweep \
  --restart-backend-between-runs \
  --update

# Results: benchmarks.json with 4 benchmarks (rate 8 updated)

# Step 3: Add high rates
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 16 --rate 24 --rate 32 \
  --delay 45 --delay 60 --delay 90 \
  --max-seconds 60 \
  --output-dir ./production-sweep \
  --restart-backend-between-runs \
  --update

# Results: benchmarks.json with 7 benchmarks (1,2,4,8,16,24,32)

# Step 4: Re-run rate 32 with pause for manual inspection
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 32 \
  --delay 90 \
  --max-seconds 60 \
  --output-dir ./production-sweep \
  --restart-backend-between-runs \
  --pause-for-enter \
  --update

# Final: benchmarks.json with 7 benchmarks (rate 32 updated with pause data)
```

## Technical Details

### Implementation

1. **Load Phase**: Before benchmarking, checks for existing `benchmarks.json` in output directory
2. **Match Phase**: After new benchmarks complete, matches by `(strategy_type, rate)` tuple
3. **Merge Phase**: Replaces matching benchmarks, keeps non-matching, adds new ones
4. **Save Phase**: Saves merged report to same output path

### Matching Function

```python
def _get_benchmark_key(benchmark) -> tuple[str, float | int | None]:
    strategy = benchmark.config.strategy
    strategy_type = strategy.type_
    
    if hasattr(strategy, "rate"):
        return (strategy_type, float(strategy.rate))
    elif hasattr(strategy, "streams"):
        return (strategy_type, int(strategy.streams))
    else:
        return (strategy_type, None)
```

## Backward Compatibility

✅ **100% Backward Compatible**
- Default behavior unchanged (overwrites file)
- Must explicitly set `--update` flag
- No impact on existing workflows

## Summary

| Feature | Description |
|---------|-------------|
| **Flag** | `--update` |
| **Type** | Boolean flag (no value) |
| **Default** | `False` (overwrite mode) |
| **Purpose** | Preserve and update existing benchmarks |
| **Matching** | By strategy type + rate/streams |
| **Use Cases** | Failed runs, incremental sweeps, iterative testing |
| **Compatibility** | Fully backward compatible |

**Perfect for**: Building comprehensive benchmark datasets incrementally without losing previous results! 🎯
