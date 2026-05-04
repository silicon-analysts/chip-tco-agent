#!/usr/bin/env bash
# Regenerate the saved example transcripts under examples/outputs/.
#
# Run this:
#   - After Step 0 fixes (system prompt + horizon_original + renderer) so the
#     committed transcripts reflect current agent behavior.
#   - After any change to chip_tco_agent.py, the system prompt, or the bundled
#     JSON snapshots.
#   - Before tagging a release.
#
# Cost: ~$1.50 in Anthropic API charges (5 queries × ~$0.30 average on Sonnet 4.5).
# Wall-clock: ~15 minutes (5 queries × ~2.5 minutes each, sequential).
#
# Usage:
#   bash scripts/regenerate_example_outputs.sh
#
# Requires: ANTHROPIC_API_KEY and SILICON_ANALYSTS_API_KEY in environment or .env.

set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p examples/outputs

run_query() {
  local label="$1"
  local query="$2"
  local outfile="examples/outputs/${label}.txt"
  echo "→ regenerating ${outfile} ..."
  uv run python chip_tco_agent.py "${query}" > "${outfile}" 2>&1
  echo "  done: $(wc -l < "${outfile}") lines"
}

run_headline() {
  local outfile="demo_output.txt"
  echo "→ regenerating ${outfile} (the headline transcript referenced in README) ..."
  uv run python chip_tco_agent.py \
    "Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East, 24-month amortization, no budget cap" \
    > "${outfile}" 2>&1
  echo "  done: $(wc -l < "${outfile}") lines"
}

run_headline
run_query "02_8b_finetune"      "Llama 3.1 8B fine-tune over 1B tokens, budget \$50K, 30-day timeline"
run_query "03_edge_inference"   "Llama 3.1 7B inference, 10ms TTFT target, EU region, low concurrency edge deployment"
run_query "04_mixed_workload"   "Mixed workload: 50% Llama 70B inference, 50% Stable Diffusion XL image gen, 24-month horizon"
run_query "05_buy_vs_rent"      "On-prem vs cloud comparison for Llama 70B inference at 200M tokens/day, 36-month horizon"

echo ""
echo "All transcripts regenerated. Spot-check before committing:"
echo "  - 03_edge_inference.txt should now flag 10ms TTFT WARNING in rationale_short"
echo "  - 02_8b_finetune.txt should display 'Horizon: 30 days' (not '1 months')"
echo "  - 02_8b_finetune.txt should suppress the \$/M tok column"
