# Design: Chip TCO Comparison Agent

## Framework choice

Raw Anthropic SDK + official MCP Python SDK.

The `client.messages.create(... tools=...)` surface has been semver-stable since
2024 and will outlive any framework abstraction we'd pick today. Every senior ML
infrastructure engineer has already written this exact loop, so the notebook
costs the reader zero new mental model — that buyer-familiarity criterion was
the deciding factor. Keeping the MCP→Anthropic tool adapter visible (rather than
hidden behind a framework) makes the notebook itself the canonical educational
artifact for "what does it actually look like to call Silicon Analysts MCP from
an Anthropic agent." And the raw `anthropic` SDK is MIT-friendly, unlike the
Claude Agent SDK which sits under Anthropic Commercial Terms — an issue when
this code gets copy-pasted into products.

Runner-up: PydanticAI. If we ever need durable long-running workflows with HITL,
we'd port to LangGraph.

## Agent topology

Single-agent ReAct loop with a forced initial planning turn.

The query is bounded (one workload spec → one ranked recommendation), the tool
set is small (6 MCP tools + 3 local), and there is no need for branching, HITL,
or parallel sub-agents. A pure ReAct loop without an explicit plan turn risks
the model firing `get_market_pulse` first and never getting to costing math; a
"produce a plan, then execute" prefix solves that cheaply. Multi-agent
supervisor topologies introduce token overhead and observability headaches that
buy us nothing here.

## Tool inventory

**Silicon Analysts MCP tools (6):**
- `get_accelerator_costs` — chip-level economics
- `calculate_chip_cost` — derived cost for untracked chips
- `get_hbm_market_data` — HBM pricing/allocation
- `get_market_pulse` — supply-chain headlines
- `get_wafer_pricing` — wafer prices by node/foundry
- `get_packaging_costs` — CoWoS/EMIB/SoIC costs

**Local tools (3):**
- `lookup_cloud_price(chip, providers)` — reads `cloud_prices.json`
- `compute_tco(...)` — does the cost arithmetic
- `respond_with_recommendation(payload)` — synthetic final-only tool, structured output

## Tool call sequencing

Typical query: 8–12 total tool calls, completed in 6–8 reasoning turns.

The canonical sequence for a Llama-70B-style query: a plan turn (no tool calls)
→ a parallel batch of `get_accelerator_costs` for the 4 candidate chips +
`get_market_pulse` for relevant supply topics → a smaller parallel batch of
`get_packaging_costs` and optionally `get_hbm_market_data` → N parallel
`lookup_cloud_price` calls (one per chip × provider cell) → a final
`compute_tco` batch → one `respond_with_recommendation` call. Steps 2 and 3
batched in parallel; the agent should aim for 5–15 total tool calls.

## Configuration

- Model: Sonnet 4.5 default; Opus 4 opt-in via env var
- Max turns: 10 (hard cap)
- Parallel tool calls: enabled
- Structured output: forced via `respond_with_recommendation` synthetic tool
- Final-turn tool_choice: explicit when turn count >= 8

## Output schema

`TCORecommendation` (Pydantic): `query_echo`, `recommendation` (rank 1 with
chip/provider/sku/qty/cost_breakdown/performance_assumptions/ha_posture),
`alternatives` (2–3 ranked), `rejected_options_summary`, `risk_flags`,
`confidence` (overall + contributing_tiers), `reasoning_summary`, `caveats`.
Full schema lives in Phase 2 implementation.

## Confidence propagation

`recommendation.confidence.overall = min(contributing_tiers)`. If any input tool
returned `confidence_tier: medium` or `low`, the final recommendation cannot be
labeled `high`. This is the trust contract with the user.

## See also

- `notebook-spec-tco-agent.md` — full research brief (in repo root for now;
  remove before public release)
- Silicon Analysts API docs: https://siliconanalysts.com/developers
- MCP integration guides: https://siliconanalysts.com/integrations
