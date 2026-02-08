# Per-Rate Delay Feature Implementation

## Overview
Implemented support for specifying different delays before each benchmark run when testing multiple rates. This allows fine-grained control over recovery time between high-intensity benchmark runs.

## Feature Description

### Command-Line Interface
The `--delay` parameter now accepts multiple values that correspond positionally to each `--rate`:

```bash
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --profile poisson \
  --rate 1 --rate 2 --rate 3 --rate 8 --rate 16 --rate 32 \
  --delay 0 --delay 0 --delay 0 --delay 10 --delay 30 --delay 60 \
  --data "/path/to/data.json" \
  --max-seconds 60
```

### Behavior Rules

1. **Positional Matching**: Each `--delay` value corresponds to the `--rate` at the same position
   - 1st delay applies before 1st rate benchmark
   - 2nd delay applies before 2nd rate benchmark
   - etc.

2. **Uniform Delay**: If only one `--delay` is specified, it applies to all benchmark runs
   ```bash
   --rate 1 --rate 2 --rate 3 --delay 5
   # All three benchmarks get 5 second delay
   ```

3. **Partial Delays**: If fewer delays than rates are specified, remaining delays default to 0
   ```bash
   --rate 1 --rate 2 --rate 3 --rate 4 --delay 0 --delay 5
   # Delays: 0s, 5s, 0s, 0s (last two default to 0)
   ```

4. **No Delay**: If `--delay` is not specified, no delays are applied (backward compatible)
   ```bash
   --rate 1 --rate 2 --rate 3
   # No delays between benchmarks
   ```

## Use Case Example

For your specific TensorRT-LLM server scenario:

```bash
guidellm benchmark run \
  --target http://192.168.2.34:8000 \
  --request-type text_completions \
  --profile poisson \
  --rate 1 --rate 2 --rate 3 --rate 4 --rate 5 --rate 6 --rate 7 \
  --rate 8 --rate 9 --rate 12 --rate 16 --rate 24 --rate 32 \
  --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 \
  --delay 10 --delay 15 --delay 20 --delay 30 --delay 45 --delay 60 \
  --data "/home/siavashi/mohamamd/tests/axon-paper-experiments/ShareGPT_V3_unfiltered_cleaned_split.json" \
  --processor meta-llama/Meta-Llama-3-8B \
  --sharegpt-format conversational \
  --compute-output-tokens-from-response \
  --token-budget-total 2047 \
  --input-length-stats \
  --max-seconds 60 \
  --use-filter-cache
```

This configuration:
- **Rates 1-7**: No delay (instant execution) - low rates don't exhaust the server
- **Rate 8**: 10 seconds recovery time
- **Rate 9**: 15 seconds recovery time
- **Rate 12**: 20 seconds recovery time
- **Rate 16**: 30 seconds recovery time
- **Rate 24**: 45 seconds recovery time
- **Rate 32**: 60 seconds recovery time - highest rate gets maximum recovery

## Implementation Details

### Modified Files

1. **`src/guidellm/__main__.py`**
   - Changed `--delay` parameter to accept multiple values using `multiple=True` and `callback=cli_tools.parse_list_floats`

2. **`src/guidellm/benchmark/schemas/generative/entrypoints.py`**
   - Changed `delay` field from `NonNegativeFloat` to `list[NonNegativeFloat] | None`

3. **`src/guidellm/benchmark/entrypoints.py`**
   - Updated `benchmark_generative_text()` to pass `args.delay` to the benchmarker

4. **`src/guidellm/benchmark/benchmarker.py`**
   - Updated `Benchmarker.run()` signature to accept `delay: list[float] | None`
   - Implemented logic to apply the appropriate delay before each benchmark run:
     - Gets delay for current benchmark index from the list
     - Defaults to 0.0 if index exceeds list length
     - Logs the delay before sleeping

### Key Implementation Logic

```python
# In benchmarker.py, inside the benchmark loop:
if delay is not None and len(delay) > 0:
    # Get delay for current benchmark (default to 0 if not specified)
    current_delay = delay[benchmark_count] if benchmark_count < len(delay) else 0.0
    if current_delay > 0.0:
        logger.info(
            f"Delaying for {current_delay} seconds before benchmark run "
            f"{benchmark_count + 1}..."
        )
        await asyncio.sleep(current_delay)
```

## Testing

Created comprehensive E2E tests in `tests/e2e/test_delay_benchmark.py`:

1. **test_uniform_delay_between_benchmarks**: Tests single delay value applying uniformly
2. **test_per_rate_delay_between_benchmarks**: Tests different delays for different rates (key feature)
3. **test_no_delay_between_benchmarks**: Tests backward compatibility (no delay)
4. **test_partial_delays_with_defaults**: Tests partial delay list with default 0 for remaining

## Backward Compatibility

The implementation maintains full backward compatibility:
- Existing commands without `--delay` work unchanged
- Single `--delay` value works as before (uniform delay)
- New multi-value `--delay` adds new functionality without breaking existing behavior

## Benefits

1. **Server Recovery Control**: Allow time for server to recover between high-intensity runs
2. **Flexible Configuration**: Different delays for different rates based on server behavior
3. **No Overhead for Low Rates**: Skip delays for low rates that don't stress the server
4. **Backward Compatible**: Existing workflows continue to work unchanged
5. **Explicit Control**: Clear, positional mapping makes behavior predictable
