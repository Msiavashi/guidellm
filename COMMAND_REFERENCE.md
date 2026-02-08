# Quick Reference: Your TensorRT-LLM Benchmark Command

## Ready-to-Use Command

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

## Execution Timeline

| Benchmark | Rate | Delay Before | Max Duration | Status |
|-----------|------|--------------|--------------|---------|
| Run 1     | 1    | 0s           | 60s          | ✓ Ready |
| Run 2     | 2    | 0s           | 60s          | ✓ Ready |
| Run 3     | 3    | 0s           | 60s          | ✓ Ready |
| Run 4     | 4    | 0s           | 60s          | ✓ Ready |
| Run 5     | 5    | 0s           | 60s          | ✓ Ready |
| Run 6     | 6    | 0s           | 60s          | ✓ Ready |
| Run 7     | 7    | 0s           | 60s          | ✓ Ready |
| Run 8     | 8    | 10s ⏱️       | 60s          | 🔄 Recovery |
| Run 9     | 9    | 15s ⏱️       | 60s          | 🔄 Recovery |
| Run 10    | 12   | 20s ⏱️       | 60s          | 🔄 Recovery |
| Run 11    | 16   | 30s ⏱️       | 60s          | 🔄 Recovery |
| Run 12    | 24   | 45s ⏱️       | 60s          | 🔄 Recovery |
| Run 13    | 32   | 60s ⏱️       | 60s          | 🔄 Recovery |

## Estimated Runtime

- **Active Benchmarking**: Up to 13 × 60s = 780s (~13 minutes)
- **Recovery Delays**: 0+0+0+0+0+0+0+10+15+20+30+45+60 = 180s (3 minutes)
- **Total**: Approximately **16 minutes** (could be less if benchmarks complete early)

## Alternative: More Conservative Recovery

If the server needs more recovery time at high rates:

```bash
# ... (same as above, but with these delay values) ...
  --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 --delay 0 \
  --delay 15 --delay 20 --delay 30 --delay 45 --delay 60 --delay 90
```

This gives:
- Rates 1-7: No delay
- Rate 8: 15s
- Rate 9: 20s
- Rate 12: 30s
- Rate 16: 45s
- Rate 24: 60s
- Rate 32: 90s (1.5 minutes)

## Validation

After running, check the output for:
1. Each benchmark should complete or hit max-seconds constraint
2. No excessive errors at high rates (if errors occur, increase delays)
3. Server should remain responsive throughout all runs
