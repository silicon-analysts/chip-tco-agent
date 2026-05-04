# mcp.so submission

**Submission URL:** TBD — verify current submission flow at https://mcp.so/.
As of April 2026 mcp.so accepts submissions via a Pull Request to a public
GitHub registry repo (the URL of which has changed once before — re-check
the "Submit" link on mcp.so before drafting the PR).

mcp.so listings are rendered from a JSON entry plus a Markdown long
description. Both are below.

## JSON entry

```json
{
  "name": "Silicon Analysts",
  "slug": "silicon-analysts",
  "vendor": "Silicon Analysts",
  "homepage": "https://siliconanalysts.com",
  "repository": "https://github.com/silicon-analysts/chip-tco-agent",
  "documentation": "https://siliconanalysts.com/developers",
  "logo": "TBD: provide a 256x256 SVG or PNG logo URL once the brand asset is ready",
  "categories": ["hardware", "data", "research", "finops"],
  "tags": ["semiconductors", "GPU", "TCO", "cost", "H100", "H200", "B200", "MI300X", "MLOps"],
  "transport": {
    "type": "streamable_http",
    "url": "https://siliconanalysts.com/api/mcp"
  },
  "auth": {
    "type": "bearer",
    "header": "Authorization",
    "envVar": "SILICON_ANALYSTS_API_KEY",
    "signup": "https://siliconanalysts.com/developers"
  },
  "pricing": {
    "free": "~10 queries/day (100 API calls/day)",
    "paid_tiers_url": "https://siliconanalysts.com/pro"
  },
  "tools": [
    {"name": "get_accelerator_costs", "description": "BOM, sell price, FP8/BF16 TFLOPS, memory, packaging for 13 tracked accelerators."},
    {"name": "calculate_chip_cost", "description": "Derive cost for a chip not in the tracked list."},
    {"name": "get_hbm_market_data", "description": "HBM3/HBM3e/HBM4 pricing, supplier shares, allocation."},
    {"name": "get_market_pulse", "description": "Curated supply-chain headlines with confidence tiers."},
    {"name": "get_wafer_pricing", "description": "300mm wafer prices by node and foundry."},
    {"name": "get_packaging_costs", "description": "CoWoS, EMIB, SoIC, InFO-PoP, FC-BGA, FC-CSP, HBM stack pricing."}
  ],
  "examples": [
    {
      "title": "Compare H100/H200/B200/MI300X for Llama 70B inference",
      "agent": "chip-tco-agent",
      "url": "https://github.com/silicon-analysts/chip-tco-agent",
      "language": "python"
    }
  ]
}
```

## Long description (Markdown — for the listing page)

# Silicon Analysts MCP server

Provenance-tagged semiconductor cost data for AI agents. Six MCP tools
covering chip BOMs, packaging costs, HBM market state, wafer pricing,
supply-chain headlines, and derived chip-cost estimates. Every response
includes `source_type`, `confidence_tier`, and `last_updated` so agents
can propagate uncertainty into their final answers rather than invent
precision.

## Why this exists

Forward-looking GPU procurement decisions are stuck between two states:

- Free comparison tools ([getdeploying.com](https://getdeploying.com),
  [computeprices.com](https://computeprices.com)) — accurate prices but no
  reasoning, no on-prem, no provenance.
- Institutional research (SemiAnalysis AI Cloud TCO Model) — gold-standard
  analysis but $30K–$100K/year and inaccessible to a 30-person AI startup.

The Silicon Analysts MCP server is the data layer that lets agents bridge
that gap. The reference implementation is the **chip-tco-agent** repo,
which compares H100/H200/B200/MI300X TCO across five cloud providers plus
on-prem in ~150 seconds for ~$0.30 in Sonnet 4.5 tokens.

## Tools

### `get_accelerator_costs(chips: list[str])`

BOM, sell price, gross margin, FP8/BF16 TFLOPS, memory, packaging,
interconnect for any of 13 tracked accelerators (H100, H200, B100, B200,
GB200, MI300X, MI355X, Gaudi 3, TPU v5p, Trainium 2, Maia 100, MTIA v2).

```python
result = await session.call_tool("get_accelerator_costs", {"chips": ["H100", "H200", "B200", "MI300X"]})
```

### `calculate_chip_cost(spec)`

Derive a cost for a chip *not* in the tracked list. Use only when the user
asks about an untracked chip (a hypothetical, a competitor SKU, a future
part).

### `get_hbm_market_data(generation?)`

HBM3 / HBM3e / HBM4 contract pricing, supplier shares (SK Hynix, Samsung,
Micron), allocation timeline. The 12–15-month HBM3e supply pressure shows
up here.

### `get_market_pulse(topics: list[str])`

Curated supply-chain headlines by topic — CoWoS-S, CoWoS-L, HBM3e,
Blackwell supply, geopolitics. Each item carries a confidence tier. Use
this to derive risk flags, never to source numerical claims.

### `get_wafer_pricing(node, foundry)`

300mm wafer prices by node (N3, N4, N5, N7, 3GAP, 4LPP, 18A) and foundry
(TSMC, Samsung, Intel). Generally not needed for inference TCO; useful for
build-cost-of-silicon questions.

### `get_packaging_costs(type)`

CoWoS-S, CoWoS-L, EMIB, SoIC, InFO-PoP, FC-BGA, FC-CSP, HBM stack pricing
per chip-class. Used to validate on-prem BOMs and surface packaging-supply
risk.

## Auth

Bearer token. Free tier (~10 queries/day) at
https://siliconanalysts.com/developers. Pro / Team / Enterprise tiers at
/pro.

## Demo

[chip-tco-agent](https://github.com/silicon-analysts/chip-tco-agent) — MIT
licensed reference implementation on raw Anthropic SDK + official MCP
Python SDK. Five worked examples, full transcripts in the repo.

## Data freshness

The server is queried real-time against a quarterly-refreshed dataset.
Per-row `last_updated` is included in every response. Agents should warn
on `last_updated > 60 days`. The chip-tco-agent demo's bundled
`cloud_prices.json` is *separate* from the MCP server (cloud SKU $/hr is
not in the MCP scope) and is updated on its own quarterly cadence.

## Provenance contract

```json
{
  "data": { ... },
  "provenance": {
    "source_type": "primary | secondary | derived | estimate",
    "confidence_tier": "high | medium | low",
    "last_updated": "2026-04-22",
    "dataset_version": "chipSpecs-v1.4"
  }
}
```

## PR submission process

If mcp.so still uses the GitHub-PR submission flow:

1. Fork the mcp.so registry repo (find the link from "Submit" on mcp.so)
2. Add a JSON entry under the appropriate path (e.g., `servers/silicon-analysts.json`)
3. Add a long-description Markdown file (this file's content)
4. Add a logo asset (TBD: provide once brand asset is ready)
5. Open a PR with the title `Add Silicon Analysts MCP server`

## Verification before submitting

- [ ] mcp.so registry repo URL confirmed
- [ ] PR template (if any) followed exactly
- [ ] Logo asset provided in the format mcp.so requires
- [ ] All URLs in the JSON entry are reachable from a fresh browser
- [ ] The chip-tco-agent repo is public
