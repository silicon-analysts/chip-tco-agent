# Building a chip-TCO agent on raw Anthropic SDK + MCP — and what we learned about agent design tradeoffs

**Companion post for `siliconanalysts.com/blog/engineering`.**
**Length: ~2,000 words.**
**Audience: Senior ML infrastructure engineers and platform leads.**

---

## The problem

If you're running a 30-person AI startup and someone needs to decide between
H100s on CoreWeave 3-year reserved versus H200s on Lambda on-demand versus
buying eight DGX nodes for a colo, the current state of the world is: you
spend three to seven days in a spreadsheet, make four sales calls, and hope.

The pain is well documented. The FinOps category leader Vantage's homepage
tagline is literally *"From spreadsheets to sanity"* — that's how endemic
spreadsheet-driven GPU comparison is. [getdeploying.com](https://getdeploying.com)
notes a **96% spread** between the highest and lowest H100 list prices as of
early 2026 ($1.25/hr at one provider, $14.90/hr at another). Engineers
normalize prices by hand, get burned by per-instance vs. per-GPU-hour traps,
and re-do the work weekly because the prices keep moving.

Build-versus-rent math is worse. There's a frequently-cited HN debate (item
36025567) where two senior engineers publicly disagreed about whether
on-prem H100s break even at 8 months of duty cycle or 25 — because nobody
has a trustable TCO model. The good ones exist: SemiAnalysis sells an
institutional AI Cloud TCO Model to hyperscalers and funds at a rumored
$30K–$100K+/year. That's the gold standard. It's also completely
inaccessible to a startup with a $50K monthly GPU spend and a single
infrastructure engineer.

The gap is: **engineer-priced, forward-looking, multi-provider plus on-prem,
conversational**. That's what we built. The artifact is a small open-source
agent ([github.com/silicon-analysts/chip-tco-agent](https://github.com/silicon-analysts/chip-tco-agent))
that takes a workload spec — model, throughput, latency target, region, time
horizon, budget — and returns a ranked TCO recommendation across five clouds
plus on-prem in about 150 seconds. The whole loop is the raw Anthropic SDK
plus the official MCP Python SDK, no framework. The cost is roughly $0.30
per query on Sonnet 4.5.

The rest of this post is the engineering log: how we built it, what we
chose, and what's still hard.

## The artifact

Here's the headline run:

```text
─── Query ────────────────────────────────────────────────────────────────────
Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East, 24-month
amortization, no budget cap

─── Ranked options ───────────────────────────────────────────────────────────
 #  Deploy  Chip  Provider   GPUs  $/M tok  24-mo $    Confidence
 1  cloud   H100  CoreWeave    2   $1.181   $86,198    medium
 2  cloud   H200  CoreWeave    2   $1.210   $88,301    medium
 3  cloud   H100  CoreWeave    1   $0.591   $43,099    medium
```

Five lines to clone and run:

```bash
git clone https://github.com/silicon-analysts/chip-tco-agent
cd chip-tco-agent
cp .env.example .env  # add ANTHROPIC_API_KEY and SILICON_ANALYSTS_API_KEY
uv sync
uv run python chip_tco_agent.py "Llama 3.1 70B inference, 100M tokens/day, US-East, 24mo"
```

Top-line numbers from real runs:

- **150 seconds** wall-clock on Sonnet 4.5
- **~19 tool calls** per query (8 MCP, 11 local), batched in parallel
- **~$0.30–0.40** uncached per query
- **5 example queries**, all working end-to-end

For the canonical query above, the agent's reasoning trace (visible in
`demo_output.txt`) walks through: shortlisting four chips (H100, H200,
B200, MI300X), disqualifying TPU v5p / Trainium 2 / Gaudi 3 / GB200 with
one-line reasons each, parallel-fetching `get_accelerator_costs` for the
shortlist plus `get_market_pulse` for HBM/CoWoS supply, looking up cloud
prices across providers, computing TCO for each viable cell, and ranking.
The recommendation is H100 × 2 on CoreWeave 3-year reserved at
$2.46/GPU-hour — not because it's cheapest in absolute terms (the H100 × 1
no-HA option is cheaper), but because it's the highest-confidence choice
that satisfies a production HA posture.

## Framework decision

The first real engineering call was: which agent framework? I evaluated
five contenders. Honest scoring as of April 2026:

| Framework | Buyer familiarity | Multi-tool maturity | 6-month stability | MCP integration |
|---|---|---|---|---|
| **Raw Anthropic SDK + `mcp` package** | Highest | 3/5 (write the loop yourself) | **5/5 — semver stable since 2024** | 4/5 (~30 LOC adapter) |
| PydanticAI | Med-high | 4/5 | 4/5 (Production/Stable since Sep 2025) | **5/5 — cleanest integration** |
| LangGraph 1.x | Highest in survey data | 5/5 (graph state, HITL, durable) | 4/5 (1.0 LTS Oct 2025) | 4/5 (`langchain-mcp-adapters`) |
| Claude Agent SDK | Low (Claude-Code users only) | 4/5 (biased toward Read/Bash/Edit) | **2/5 — 0.1.x, Alpha classifier** | 5/5 |
| OpenAI Agents SDK | High | 5/5 | 4/5 | 5/5 |

We picked the raw SDK. Three decisive arguments:

**1. Aging well.** The `client.messages.create(..., tools=...)` surface
has been semver-stable since 2024. The notebook will still run unmodified
in 12 months. Claude Agent SDK 0.1.x will almost certainly have moved its
API by then; LangGraph 1.x has already been through a couple of breaking
1.0.x patches. For a marquee notebook that's going to be cloned by
strangers and read in tutorials, stability is the load-bearing property.

**2. Buyer familiarity.** The audience for this notebook is senior ML
infrastructure engineers. Every one of them has already written this loop.
Zero new mental model. LangGraph's graph DSL adds a learning tax;
Claude Agent SDK's CLI-subprocess architecture is *unfamiliar and
surprising* — exactly the wrong vibe for a "look how easy our API is"
artifact.

**3. License hygiene.** Claude Agent SDK is governed by Anthropic
Commercial Terms, not MIT or Apache. Notebook code gets copy-pasted into
products. The raw `anthropic` SDK is unambiguously safe.

The runner-up was PydanticAI. Its MCP integration is the cleanest of the
five (about 5 lines vs. the raw SDK's 30), and its team has a strong track
record. If we ship a community-contributed `pydantic_ai_variant.py`, that's
where we'd put it.

The case where we'd pick differently: durable long-running workflows with
HITL gates. For a "submit tapeout decision for human review" use case,
LangGraph's `create_react_agent` plus checkpointing is the right tool. Not
for a 30-second TCO query.

## The trust contract

The hardest design decision in this build wasn't framework choice or output
format. It was: **what does the agent do when it doesn't know?**

Every response from the Silicon Analysts MCP tools carries
`provenance.{source_type, confidence_tier, last_updated}`. The
`confidence_tier` is one of `high`, `medium`, `low`. The contract we picked
is:

> **`recommendation.confidence.overall = min(contributing_tiers)`**

If any input the agent used was medium-confidence, the final recommendation
cannot be labeled high. Period. The user sees a yellow badge and an
explicit "low confidence inputs: …" line.

This is enforced **in code, not just in the prompt**. The system prompt
tells the agent to do this — but agents trained on RLHF tend to round up
toward confidence. So the agent loop runs `min()` over
`contributing_tiers` after the agent returns, and clamps `overall` if the
model claimed higher. If we override, a caveat is appended:

```python
result.caveats.append(
    f"[trust contract] Overall confidence was downgraded from "
    f"'{original}' to '{min_tier}' to match the lowest contributing tier."
)
```

The concrete example that made this design decision real: there is no
public B200 FP8 throughput benchmark on Llama 70B as of 2026-04-30. Lambda
published a B200 MLPerf v5.1 result, but it's FP4, not FP8. The honest
move is to halve the FP4 number as a rough estimate and tag the result
`medium` confidence. We did. The agent now flags B200 with a medium-tier
caveat whenever B200 appears in a recommendation, and the overall
confidence on the headline query is `medium` — not `high` — because of
that single tier.

We got pushback during testing. "Why not just label it high if the rest of
the data is high?" Because the user is making a procurement decision. If
the B200 throughput estimate is off by 30% we want them to know that's a
risk before they sign a 3-year contract, not after.

This is the line that separates this notebook from the agentic-FinOps
demos that confidently invent prices. Provenance metadata is doing real
work here, and the user-visible confidence badge is the entire point.

## What's still hard

A few things the launch version doesn't do well, in decreasing order of
how much they bother me:

**1. Cloud pricing data freshness.** The bundled `cloud_prices.json` is a
snapshot dated `2026-04-30` with explicit `last_verified` per cell. The
agent warns when it's older than 60 days. We refresh quarterly. The honest
question I want feedback on: is a snapshot OK, or should this be a runtime
scrape against the providers' pricing APIs? Snapshots are reproducible
and PR-friendly; scrapes track weekly drift but introduce rate-limit and
consent surfaces, and the providers often mismatch their public pricing
pages from their billing API responses. Open question.

**2. Multi-modal workloads.** Example 04 is *"Mixed workload: 50% Llama
70B inference, 50% Stable Diffusion XL image gen, 24-month horizon"*. The
agent decomposes the workload — recognizes that the LLM half wants memory
bandwidth and the image-gen half wants tensor cores — but doesn't fully
size both sub-clusters. The output ranks single-cluster solutions and
flags the heterogeneity as a caveat. A proper fix means the agent needs
to model heterogeneous fleets, which is bigger than the structured-output
schema we picked.

**3. Edge accelerators.** Silicon Analysts tracks 13 datacenter chips.
There's no L40S, no Jetson AGX, no Apple M-series, no Coral. If your
workload is edge-first, the agent will tell you — but it'll only compare
the data-center chips it has data for.

**4. Hard latency constraints.** When the user states "10ms TTFT target"
and no candidate option meets it, earlier versions of the agent silently
ranked the closest option as #1 with the constraint failure buried in
caveats. The current version (post Step 0 of Phase 3) treats this as an
explicit failure mode: rank order #1 carries a `WARNING: No option meets
your stated [X] constraint of [value]` as the FIRST sentence of
`rationale_short`, and `confidence.overall` is forced to `low`. This is
the kind of bug that's only visible once you run a representative range
of queries.

## What we want from the agent-developer community

Three asks. These are the same asks I'm posting on Show HN; they're worth
restating here for the developer audience that finds the blog post first.

1. **Is the worked example defensible?** If you actually buy this hardware
   and the numbers look wrong for your region, please open an issue with
   `cloud_prices.json` cells you'd correct.

2. **Did we pick the right framework?** Raw Anthropic SDK + official MCP
   over LangGraph and Claude Agent SDK. We argued ourselves into it; we'd
   genuinely like to hear from people who'd argue out.

3. **Snapshot vs. runtime scrape for cloud pricing.** This is the part of
   the implementation most likely to rot. Snapshot is honest and
   PR-friendly. Scrape is real-time but adds rate-limit and consent
   surface. Curious which tradeoff your team would prefer.

A specific invitation: if you've built a similar agent — chip selection,
GPU procurement support, FinOps decision support — what did you choose
differently? Where did you land on the structured-output question, the
provenance-and-confidence question, the snapshot-vs-scrape question? The
field is small enough that we should be comparing notes.

The repo is at [github.com/silicon-analysts/chip-tco-agent](https://github.com/silicon-analysts/chip-tco-agent).
The full architectural log lives in `docs/design.md`. The fully-populated
research brief that we worked from is in the repo root as
`notebook-spec-tco-agent.md`.

This is one notebook. The bigger play is that semiconductor cost data is a
domain where provenance matters more than fluency, and confidence
propagation matters more than confident answers. If you're building agents
in domains with the same shape — power systems, supply chain, materials,
biotech — the patterns here transfer. Please tell us where they break.
