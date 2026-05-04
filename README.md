# Chip TCO Comparison Agent

> Compare H100, H200, B200, and MI300X TCO across cloud providers and on-prem in one query.

```text
─── Query ─────────────────────────────────────────────────────────────────────
Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East, 24-month
amortization, no budget cap

─── Ranked options ────────────────────────────────────────────────────────────
 #  Deploy  Chip  Provider   GPUs  $/M tok  24-mo $    Confidence
 1  cloud   H100  CoreWeave    2   $1.181   $86,198    medium
 2  cloud   H200  CoreWeave    2   $1.210   $88,301    medium
 3  cloud   H100  CoreWeave    1   $0.591   $43,099    medium

19 tool calls (8 MCP, 11 local) · 4 turns · 150s · ~$0.39 on Sonnet 4.5
```

A full transcript of this run is in [`demo_output.txt`](demo_output.txt). Four
more example queries (8B fine-tune, 7B edge inference, mixed workload, on-prem
vs cloud) are saved under [`examples/outputs/`](examples/outputs/).

## What it does

You describe a workload — model, throughput, latency target, region, time
horizon, budget. The agent picks a shortlist of accelerators, fetches per-chip
economics from the [Silicon Analysts MCP server](https://siliconanalysts.com/developers),
looks up cloud `$/GPU-hr` from a bundled snapshot, computes on-prem TCO with
explicit power and colocation assumptions, and returns a ranked recommendation
with provenance and confidence tiers.

The whole loop is the raw [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python)
plus the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
No agent framework, no abstraction layer — the loop is in
[`chip_tco_agent.py`](chip_tco_agent.py) and is short enough to read in one sitting.

## Quickstart

```bash
git clone https://github.com/silicon-analysts/chip-tco-agent
cd chip-tco-agent
cp .env.example .env  # add ANTHROPIC_API_KEY and SILICON_ANALYSTS_API_KEY
uv sync
uv run python chip_tco_agent.py "Llama 3.1 70B inference, 100M tokens/day, US-East, 24mo"
```

A run takes ~150 seconds and ~$0.30–0.40 in Anthropic API charges on Sonnet 4.5.

## Example queries

### 1. Llama 70B inference at scale

> *"Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East, 24-month amortization, no budget cap"*

```text
 1  cloud  H100  CoreWeave  2  $1.181  $86,198  medium
 2  cloud  H200  CoreWeave  2  $1.210  $88,301  medium
 3  cloud  H100  CoreWeave  1  $0.591  $43,099  medium

Recommendation: H100 × 2 on CoreWeave 3yr reserved at $2.46/GPU-hr.
Mature PyTorch/vLLM ecosystem, no supply risk, 2.3× headroom at 70% utilization.
HBM3e supply is medium-risk (TrendForce reports 12–15-month lead times); does
not affect H100 directly.
```

Full transcript: [`demo_output.txt`](demo_output.txt)

### 2. Llama 8B fine-tune within budget

> *"Llama 3.1 8B fine-tune over 1B tokens, budget $50K, 30-day timeline"*

```text
 1  cloud  H100 SXM5  GCP     2  $3,285  high      ← spot
 2  cloud  H100 SXM5  Lambda  2  $5,825  high      ← on-demand fallback
 3  cloud  MI300X     Azure   2  $4,818  medium

Recommendation: GCP H100 spot at $2.25/GPU-hr. Checkpoint every 1–2h to
mitigate preemption; historical preemption rate <10% for ML workloads.
```

The agent recognized the 30-day horizon, dropped 3-year-reserved pricing
from consideration, and pulled GCP spot tier into the shortlist. Full
transcript: [`examples/outputs/02_8b_finetune.txt`](examples/outputs/02_8b_finetune.txt)

### 3. On-prem vs cloud at higher volume

> *"On-prem vs cloud comparison for Llama 70B inference at 200M tokens/day, 36-month horizon"*

```text
 1  cloud    H100 × 2  CoreWeave 3yr   3yr cost  $129,298   medium
 2  cloud    H200 × 2  CoreWeave 3yr   3yr cost  $132,452   medium
 3  on-prem  H100 × 8  Self-managed    3yr TCO   $568,000   medium  ← only beats cloud at >70% util

Recommendation: still cloud at this scale. Crossover utilization ~73% sustained
(per onprem_assumptions.json). At 200M tokens/day on 2× H100 with HA, sustained
utilization is ~14% — far below the on-prem break-even.
```

Full transcript: [`examples/outputs/05_buy_vs_rent.txt`](examples/outputs/05_buy_vs_rent.txt)

## How it works

The agent follows a **single-agent ReAct loop** with a forced initial planning
turn:

1. **Plan turn.** The model emits a plain-text plan listing candidate
   accelerators (typically 4 of the 13 tracked chips), the data it needs to
   fetch, and the comparison axes. Disqualified chips are listed with one-line
   reasons. No tool calls yet.
2. **Parallel batch.** `get_accelerator_costs` for each candidate chip plus
   `get_market_pulse` for relevant supply topics — typically 5–8 tool calls
   in one turn, dispatched concurrently via `asyncio.gather`.
3. **Compute turn.** `lookup_cloud_price` (local, reads `cloud_prices.json`)
   and `compute_tco` (local, applies on-prem TCO arithmetic from
   `onprem_assumptions.json`) for each candidate. Another parallel batch.
4. **Final turn.** The agent calls `respond_with_recommendation` with a
   Pydantic-validated JSON payload. The Pydantic model (`TCORecommendation`)
   is the same schema referenced in the system prompt's output-format block.

Two safety rails the user gets for free:

- **Final-turn forcing**: at turn ≥ 8, `tool_choice` is set to
  `respond_with_recommendation` so the agent cannot drift past the 10-turn cap.
- **Trust-contract enforcement**: after the agent returns, the loop runs
  `min()` over `confidence.contributing_tiers` and clamps `confidence.overall`
  if the model claimed a higher tier than the data justifies. If we override,
  a caveat is appended to the response.

See [`docs/design.md`](docs/design.md) for the architectural decision log
(framework choice, agent topology, output schema, confidence propagation).

## Configuration

| Env var | Required | Default | Notes |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Get at https://console.anthropic.com |
| `SILICON_ANALYSTS_API_KEY` | Yes | — | Free tier ~10 queries/day at https://siliconanalysts.com/developers |
| `SILICON_ANALYSTS_MCP_URL` | No | `https://siliconanalysts.com/api/mcp` | |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-5` | Use `claude-opus-4` for harder queries (~5× cost) |
| `MAX_AGENT_TURNS` | No | `10` | Hard cap on reasoning turns |

## Cost per query

Measured on real runs of the five example queries:

| Query | Tool calls | Turns | Wall-clock | API cost (Sonnet 4.5) |
|---|---:|---:|---:|---:|
| Headline (Llama 70B) | 19 | 4 | 150s | $0.39 |
| 8B fine-tune | 19 | 4 | 146s | $0.29 |
| 7B edge inference | ~16 | 3–4 | ~120s | ~$0.25 |
| Mixed workload | ~18 | 4 | ~140s | ~$0.30 |
| Buy vs rent | ~18 | 4 | ~140s | ~$0.30 |

**Average: ~$0.30–0.40 per query, uncached.** With prompt caching (the system
prompt is ~2K tokens and stable across queries), expected steady-state cost
drops to ~$0.04–0.10 per query — a ~5–8× reduction. Caching is not enabled in
the current implementation; it's a clean post-launch optimization.

Opus 4 is approximately 5× the price of Sonnet 4.5 per token. We've not
observed enough quality lift on these queries to justify the default.

## Limitations

This is a marquee notebook. There are real gaps you should know about before
trusting it for a procurement decision:

- **B200 FP8 throughput on Llama 70B is estimated, not measured.** The MLPerf
  v5.1 result we have is FP4-only; we halve it to estimate FP8. The agent flags
  this as `confidence_tier: medium` whenever B200 appears in a recommendation.
  Once a public B200 FP8 70B benchmark appears, we'll update `perf_benchmarks.json`.
- **Cloud pricing is a snapshot.** `cloud_prices.json` is dated `2026-04-30`
  with explicit `last_verified` per cell. The agent warns if the snapshot is
  >60 days old. We refresh quarterly. Pricing for AWS/Azure/GCP reserved tiers
  is computed from public discount tiers (Savings Plans, RIs, CUDs) and
  marked `confidence: medium`.
- **EU pricing coverage is thin.** The bundled snapshot is US-centric. EU
  cells are mostly null; the agent will flag this and recommend US options.
- **Multi-modal workloads are not cleanly handled.** Example 04 (mixed Llama +
  SDXL) produces incomplete sizing for the image-gen half. The agent decomposes
  the workload but doesn't fully size both sub-clusters.
- **Hyperscaler ASICs (Trainium 2, Maia 100, MTIA v2) and edge accelerators
  are out of scope.** Silicon Analysts tracks 13 chips; the agent will tell
  you if your workload would benefit from a chip outside that set.
- **You bring your own LLM access.** This repo doesn't proxy Anthropic
  requests; you need your own `ANTHROPIC_API_KEY`.

The trust contract is `confidence.overall = min(contributing_tiers)`. If any
input was medium-confidence, the recommendation cannot be labeled high. We
prefer surfacing uncertainty over inventing precision.

## Architecture

```
┌─────────────┐     ┌────────────────┐     ┌──────────────────────┐
│ Your query  │ ──> │ chip_tco_agent │ ──> │ TCORecommendation    │
└─────────────┘     │  (ReAct loop)  │     │  (Pydantic-validated)│
                    └───────┬────────┘     └──────────────────────┘
                            │
                ┌───────────┼───────────────┐
                ↓           ↓               ↓
       ┌─────────────┐ ┌──────────┐ ┌────────────────┐
       │ Anthropic   │ │ Silicon  │ │ Local helpers  │
       │ Claude      │ │ Analysts │ │ • cloud_prices │
       │ (LLM)       │ │ MCP      │ │ • compute_tco  │
       │             │ │ (6 tools)│ │ • onprem TCO   │
       └─────────────┘ └──────────┘ └────────────────┘
```

The notebook ([`chip_tco_agent.ipynb`](chip_tco_agent.ipynb)) walks through
the loop cell-by-cell with explanations between each piece. The CLI
([`chip_tco_agent.py`](chip_tco_agent.py)) is the same logic in one file.

## Built on

- [Silicon Analysts API](https://siliconanalysts.com) — chip-level cost data with provenance
- [Anthropic Claude](https://anthropic.com) — LLM reasoning
- [Model Context Protocol](https://modelcontextprotocol.io) — tool integration over Streamable HTTP
- [Pydantic 2](https://docs.pydantic.dev/) — structured output validation
- [Rich](https://github.com/Textualize/rich) — terminal rendering

## Contributing

Issues and PRs welcome. Especially helpful:

- **Fix prices for your region.** `cloud_prices.json` is the part most likely
  to drift. PR a cell with a `last_verified` date and a source URL.
- **Add a chip we missed.** Trainium 3, Gaudi 3 inference, MI355X, etc. — the
  Silicon Analysts MCP server is the source of truth for chip economics; if
  it's tracked there, the agent should be able to use it.
- **A real B200 FP8 70B benchmark.** This is the highest-value single
  contribution right now — it would let us drop the medium-confidence flag
  on B200 throughout.

Out of scope for this repo: agent-framework swaps (LangGraph variant,
PydanticAI variant), commercial integrations, billing logic.

## License

MIT — see [LICENSE](LICENSE).

## Built by

[Silicon Analysts](https://siliconanalysts.com) — semiconductor data and analysis platform with an MCP server for AI agents.
