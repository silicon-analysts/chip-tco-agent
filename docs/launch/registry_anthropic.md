# Anthropic MCP connector directory submission

**Submission URL:** TBD — verify current submission URL. As of April 2026
the connector directory has been distributed across (a) the Claude Desktop
connector marketplace UI, (b) `github.com/modelcontextprotocol/servers`
(community list), and (c) Anthropic-curated launch posts. Re-check
https://docs.anthropic.com/en/docs/mcp and the Anthropic developer changelog
before submitting.

## Server identity

| Field | Value |
|---|---|
| Server name | **Silicon Analysts** |
| Tagline | Semiconductor cost data and market intelligence for AI agents. |
| Vendor | Silicon Analysts |
| Homepage | https://siliconanalysts.com |
| Developer docs | https://siliconanalysts.com/developers |
| Repository (demo) | https://github.com/silicon-analysts/chip-tco-agent |
| MCP version | Latest (Streamable HTTP transport) |
| MCP endpoint | `https://siliconanalysts.com/api/mcp` |
| License (server) | Proprietary; data licensed to API users under the Silicon Analysts terms at /developers |
| License (demo agent) | MIT |

## Description (1–2 sentences)

> Silicon Analysts is an MCP server that exposes provenance-tagged
> semiconductor cost data — chip BOMs, packaging costs, HBM market state,
> wafer pricing, and supply-chain pulse — to AI agents over Streamable HTTP.
> Every response carries `provenance.{source_type, confidence_tier,
> last_updated}` so agents can propagate uncertainty into their final
> answers instead of inventing precision.

## Auth

- **Method**: API key via Bearer token in the `Authorization` header.
- **How to get one**: Free tier at https://siliconanalysts.com/developers.
  Sign in with email or Google SSO, generate a key, copy once
  (`sa_live_...`), paste into the agent's `.env` as
  `SILICON_ANALYSTS_API_KEY`.
- **Free tier**: ~10 queries/day (100 API calls/day; one chip-TCO-agent query
  uses ~10 calls). Pro tier (~10K calls/hour) at /pro.

## Tool list

The server exposes **6 tools**. The chip-TCO-agent demo notebook calls 4–6
of them per query.

| Tool | One-line description | Example |
|---|---|---|
| `get_accelerator_costs` | BOM, sell price, gross margin, FP8/BF16 TFLOPS, memory, packaging, interconnect for any of 13 tracked accelerators. | `get_accelerator_costs(chips=["H100","H200","B200","MI300X"])` |
| `calculate_chip_cost` | Derive a cost estimate for a chip *not* in the tracked list (a hypothetical, a competitor SKU, a future part). | `calculate_chip_cost(spec={"node":"3nm","die_mm2":600,"hbm_gb":192})` |
| `get_hbm_market_data` | HBM3 / HBM3e / HBM4 contract pricing, supplier shares (SK Hynix, Samsung, Micron), allocation timeline. | `get_hbm_market_data(generation="HBM3e")` |
| `get_market_pulse` | Curated supply-chain headlines by topic (CoWoS-S/L, HBM, Blackwell supply, geopolitics) with confidence tiers. Use to derive risk flags, never to source numerical claims. | `get_market_pulse(topics=["CoWoS-L","HBM3e","Blackwell supply"])` |
| `get_wafer_pricing` | 300mm wafer prices by node and foundry (TSMC N3/N4/N5/N7, Samsung 3GAP/4LPP, Intel 18A). | `get_wafer_pricing(node="N3",foundry="TSMC")` |
| `get_packaging_costs` | CoWoS-S, CoWoS-L, EMIB, SoIC, InFO-PoP, FC-BGA, FC-CSP, HBM stack pricing per chip-class. | `get_packaging_costs(type="CoWoS-L")` |

## Tracked accelerators (13)

H100, H200, B100, B200, GB200, MI300X, MI355X, Gaudi 3, TPU v5p,
Trainium 2, Maia 100, MTIA v2, plus one in-progress addition. The
authoritative list is the response from `get_accelerator_costs`.

## Demo / reference implementation

**Repo**: https://github.com/silicon-analysts/chip-tco-agent

A single-agent ReAct loop on the raw Anthropic SDK + the official MCP
Python SDK. Takes a workload spec and returns a ranked TCO recommendation
across cloud providers and on-prem in ~150 seconds. Cost: ~$0.30–0.40 per
query on Sonnet 4.5. Five worked examples, all transcripts in the repo.

```bash
git clone https://github.com/silicon-analysts/chip-tco-agent
cd chip-tco-agent
cp .env.example .env  # add ANTHROPIC_API_KEY and SILICON_ANALYSTS_API_KEY
uv sync
uv run python chip_tco_agent.py "Llama 3.1 70B inference, 100M tokens/day, US-East, 24mo"
```

## Data freshness model (be transparent)

- **Chip BOMs and accelerator costs**: refreshed quarterly; per-row
  `last_updated` is included in every response.
- **HBM market data**: refreshed monthly.
- **Market pulse / supply-chain headlines**: refreshed weekly.
- **Wafer pricing and packaging costs**: refreshed quarterly with foundry
  earnings.

The bundled `cloud_prices.json` in the demo repo is a *snapshot* (not part
of the MCP server itself) dated 2026-04-30 with explicit `last_verified`
per cell. The agent warns when it's older than 60 days.

## Provenance contract

Every tool response includes:

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

Agents that propagate `min(confidence_tier)` into their final output
deliver more honest recommendations than agents that don't. The chip-TCO
demo enforces this in code, not just in the prompt.

## Pricing for end users

- **Free** — ~10 queries/day, all 6 tools, read-only.
- **Pro** ($299/mo) — ~10K calls/hour, priority support, dashboard.
- **Team** ($1,499/mo) — same plus quarterly model TCO review by a human
  analyst.
- **Enterprise** — custom, priced as 1–2% of GPU spend.

Pricing is current as of the launch date and may evolve based on usage
patterns.

## Submission contact

- Primary: Silicon Analysts team via https://siliconanalysts.com/contact
- Issues with the demo: https://github.com/silicon-analysts/chip-tco-agent/issues
- Issues with the MCP server itself: https://siliconanalysts.com/developers
  (or [issues@siliconanalysts.com](mailto:issues@siliconanalysts.com) — TBD whether this is wired)
