# Example transcripts

Saved stdout from running each `examples/0X_*.py` script with real Anthropic
and Silicon Analysts API credentials. Useful as:

- README references for users browsing the repo
- Show HN evidence ("does this work for X?" → "see `examples/outputs/`")
- Regression baselines for future runs (`diff` against a fresh transcript
  surfaces behavior changes)

## Files

| File | Query |
|---|---|
| `02_8b_finetune.txt` | Llama 3.1 8B fine-tune over 1B tokens, budget $50K, 30-day timeline |
| `03_edge_inference.txt` | Llama 3.1 7B inference, 10ms TTFT target, EU region, low concurrency edge |
| `04_mixed_workload.txt` | Mixed workload: 50% Llama 70B + 50% SDXL, 24-month horizon |
| `05_buy_vs_rent.txt` | On-prem vs cloud, Llama 70B at 200M tokens/day, 36-month horizon |

The headline query (Llama 70B inference, 100M tokens/day) is saved one level
up in [`../../demo_output.txt`](../../demo_output.txt).

## Regenerating

These transcripts go stale whenever:

- The system prompt changes
- A bundled JSON snapshot is updated (`cloud_prices.json`,
  `onprem_assumptions.json`, `perf_benchmarks.json`)
- The Rich renderer changes
- A new chip is added to the Silicon Analysts MCP server

Regenerate all five plus the headline:

```bash
bash scripts/regenerate_example_outputs.sh
```

Cost: ~$1.50 in Anthropic API charges. Time: ~15 minutes sequential.

## Note on dates

The committed transcripts may predate later code changes. Check the footer
line of each transcript for the actual run date and the `cloud_prices.json`
`as_of` value. If the agent's behavior in your run differs noticeably from
the saved version, regenerate.
