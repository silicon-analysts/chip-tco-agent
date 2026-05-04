# Smithery.ai submission

**Submission URL:** TBD — verify current submission flow at
https://smithery.ai/. As of April 2026 Smithery accepts submissions via
either (a) the publish flow in their CLI / web UI for hosted servers, or
(b) a PR to a public registry repo on GitHub. Re-check before submitting.

Smithery's submission format is YAML-flavored and tighter than the
Anthropic directory entry. Keep the description compact.

## Server YAML

```yaml
name: silicon-analysts
displayName: Silicon Analysts
description: |
  Provenance-tagged semiconductor cost data — chip BOMs, packaging costs,
  HBM market state, wafer pricing, supply-chain pulse — for AI agents.
  Every response carries source_type, confidence_tier, and last_updated so
  agents can propagate uncertainty rather than invent precision.
homepage: https://siliconanalysts.com
repository: https://github.com/silicon-analysts/chip-tco-agent
docs: https://siliconanalysts.com/developers
license: Proprietary (data); MIT (demo agent)

transport:
  type: streamable_http
  url: https://siliconanalysts.com/api/mcp

auth:
  type: bearer
  envVar: SILICON_ANALYSTS_API_KEY
  signupUrl: https://siliconanalysts.com/developers
  freeTier: ~10 queries/day (100 API calls/day)

categories:
  - hardware
  - finance
  - data
  - research

keywords:
  - semiconductors
  - GPU
  - TCO
  - cost-modeling
  - cloud-pricing
  - H100
  - H200
  - B200
  - MI300X
  - MLOps
  - FinOps

tools:
  - name: get_accelerator_costs
    description: BOM, sell price, gross margin, FP8/BF16 TFLOPS, memory, packaging, interconnect for any of 13 tracked accelerators.
  - name: calculate_chip_cost
    description: Derive a cost estimate for a chip not in the tracked list.
  - name: get_hbm_market_data
    description: HBM3/HBM3e/HBM4 contract pricing, supplier shares, allocation.
  - name: get_market_pulse
    description: Curated supply-chain headlines by topic with confidence tiers. Use for risk flags, not numerical claims.
  - name: get_wafer_pricing
    description: 300mm wafer prices by node and foundry.
  - name: get_packaging_costs
    description: CoWoS-S/L, EMIB, SoIC, InFO-PoP, FC-BGA, FC-CSP, HBM stack pricing per chip-class.

demoAgent:
  name: chip-tco-agent
  url: https://github.com/silicon-analysts/chip-tco-agent
  language: python
  description: |
    Takes a workload spec ("Llama 70B inference, 100M tokens/day, p99 <500ms,
    24mo amortization") and returns a ranked TCO recommendation across cloud
    providers and on-prem in ~150 seconds. Built on raw Anthropic SDK + MCP
    Python SDK, no agent framework. Cost ~$0.30–0.40 per query on Sonnet 4.5.

dataFreshness:
  cadence: quarterly (bom/wafer/packaging), monthly (hbm), weekly (market pulse)
  staleness_warning: agent flags any response with last_updated > 60 days
  snapshot_or_realtime: live (server queries are real-time against the dataset)
```

## Long description (Markdown)

> Silicon Analysts is an MCP server that exposes the kind of semiconductor
> cost data that used to live in $30K–$100K/year institutional research
> reports — chip BOMs, packaging costs, HBM market state, wafer pricing,
> supply-chain headlines — through six MCP tools, with a free tier
> sufficient for ~10 queries/day.
>
> The differentiator is **provenance**. Every response includes
> `source_type` (primary vs. secondary vs. derived vs. estimate),
> `confidence_tier` (high / medium / low), and `last_updated`. Agents that
> propagate `min(confidence_tier)` to their final output deliver honest
> recommendations: when a B200 FP8 70B benchmark doesn't exist publicly,
> the server flags the estimate as `medium` and the downstream agent's
> overall confidence is forced to medium. No fake precision.
>
> The reference implementation is **chip-tco-agent**: an open-source
> single-agent ReAct loop on raw Anthropic SDK + official MCP Python SDK
> that takes a workload spec and returns a ranked TCO recommendation
> across AWS, Azure, GCP, CoreWeave, Lambda, and on-prem in ~150 seconds.
> Five worked examples, full transcripts in the repo, MIT licensed.
>
> Free tier: 100 API calls/day (~10 queries). Get a key at
> https://siliconanalysts.com/developers. Pro/Team/Enterprise tiers
> documented at /pro.

## Verification before submitting

- [ ] MCP endpoint at `https://siliconanalysts.com/api/mcp` responds to
      `initialize` with the correct server identity
- [ ] `list_tools` returns all 6 tools with current input schemas
- [ ] A free-tier key from /developers can call each tool successfully
- [ ] The chip-tco-agent repo is public and `uv sync` resolves cleanly
- [ ] The repository's `docs/launch/registry_smithery.md` entry (this file)
      stays in sync with whatever ends up live on smithery.ai
