# Show HN post draft

## Title (≤80 chars, post this exact text)

```
Show HN: An MCP agent that compares H100/H200/B200/MI300X TCO in 30 seconds
```

(78 chars. Concrete chips, no superlatives.)

## URL

```
https://github.com/silicon-analysts/chip-tco-agent
```

## Post body

> Hi HN — we built a small open-source notebook that takes a workload spec
> like *"Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East,
> 24-month amortization"* and returns a ranked TCO recommendation across
> AWS, Azure, GCP, CoreWeave, Lambda, and on-prem. Real run on the headline
> query: 19 tool calls (8 MCP, 11 local), 4 reasoning turns, 150 seconds,
> $0.39 in Sonnet 4.5 tokens. Ranked output:
>
> ```
>  1  cloud  H100  CoreWeave  2  $1.181/M tok  $86,198 / 24mo  medium
>  2  cloud  H200  CoreWeave  2  $1.210/M tok  $88,301 / 24mo  medium
>  3  cloud  H100  CoreWeave  1  $0.591/M tok  $43,099 / 24mo  medium  (no HA)
> ```
>
> It's a single-agent ReAct loop on the **raw Anthropic SDK + the official
> MCP Python SDK** — no LangGraph, no Claude Agent SDK, no framework
> abstractions. The agent calls 6 MCP tools we maintain (chip-level BOMs,
> packaging costs, HBM market data, supply-chain pulse, wafer pricing, derived
> cost helpers) plus a bundled `cloud_prices.json` snapshot dated 2026-04-30
> with explicit `last_verified` per row. Code is in one ~1500-line Python
> file you can read top-to-bottom.
>
> The thing we tried hardest to get right is **honesty about confidence**.
> Every API response carries `provenance.{source_type, confidence_tier,
> last_updated}`, and the agent's final recommendation surfaces `min()` of
> those tiers as a badge. The trust contract is enforced in code, not just
> in the prompt — if the model claims `confidence: high` but any input was
> medium, the loop clamps it down and adds a caveat. Concrete example: there
> is no public B200 FP8 70B benchmark as of 2026-04-30, so the agent flags
> that branch `medium` rather than inventing a number from the FP4 result.
> We'd rather surface uncertainty than fake precision — that's the whole
> point of building this on top of provenance-tagged data.
>
> Three things we'd love feedback on:
>
> 1. **Is the worked example defensible?** The repo has `demo_output.txt` for
>    the headline query and four more under `examples/outputs/`. If you
>    actually buy GPUs at this scale and the numbers look wrong for your
>    region or workload, please open an issue.
> 2. **Framework choice.** We picked raw SDK over LangGraph and the Claude
>    Agent SDK for stability, buyer-familiarity, and license hygiene. Would
>    you have picked differently?
> 3. **Snapshot vs. runtime scrape for `cloud_prices.json`.** A snapshot is
>    honest, reproducible, and easy to PR; runtime scraping would track
>    weekly drift but adds rate-limit and consent surface. Curious which
>    tradeoff your team would prefer.
>
> Cost-per-query lands at ~$0.30–0.40 uncached on Sonnet 4.5; we expect
> ~$0.04–0.10 with prompt caching enabled (post-launch). Free Silicon
> Analysts API tier covers ~10 queries/day. Repo is MIT, no commercial
> strings.

## Word count

~370 words. Target was ≤500. Good headroom.

## Posting checklist

- [ ] Repo is public on GitHub before posting
- [ ] `demo_output.txt` and `examples/outputs/*.txt` are committed and linked
      from the README
- [ ] Free-tier API key flow at `siliconanalysts.com/developers` is verified
      working (this is going to get hammered)
- [ ] Status page is reachable
- [ ] Post between 8:00–9:00 AM Eastern on a Tuesday/Wednesday/Thursday
      (best Show HN windows historically)
- [ ] Be at the keyboard for the next 4 hours to answer comments — Show HN
      threads die fast if the author doesn't engage in the first hour
- [ ] First-comment plant: a comment from the author with the 5-line clone-
      and-run snippet, the demo_output.txt link, and the three asks repeated
      verbatim. Posters who do this get more discussion than those who don't.

## Comment-thread responses to pre-write

These are the predictable questions; have replies ready in a scratchpad.

**"Why not LangGraph / Claude Agent SDK?"** — Stability and license. The raw
`messages.create(... tools=...)` surface has been semver-stable since 2024.
Claude Agent SDK is still 0.1.x with an Alpha PyPI classifier and is
governed by Anthropic Commercial Terms (not MIT). LangGraph is excellent
for branching/HITL workflows but adds a graph DSL we don't need for a
bounded single-query loop. PydanticAI was the strongest runner-up;
considering a `pydantic_ai_variant.py` in `examples/` if there's interest.

**"Cloud prices are wrong for my region."** — Likely true. The bundled
snapshot is US-centric. PRs welcome with `last_verified` dates and source
URLs. The agent warns users when the snapshot is >60 days old.

**"How do you handle B200 benchmarks?"** — Honestly. No public Llama 70B FP8
benchmark exists for B200 as of 2026-04-30. We halve the public FP4 result
from Lambda's MLPerf v5.1 submission and tag it `confidence_tier: medium`.
The agent surfaces this as a risk flag whenever B200 appears in a
recommendation. When a public FP8 70B benchmark appears, we'll update
`perf_benchmarks.json` and re-tag.

**"What about [Cerebras / Groq / SambaNova / etc]?"** — Out of scope today.
Silicon Analysts tracks 13 chips (the H100/H200/B100/B200/GB200 NVIDIA line,
MI300X/MI355X AMD, Gaudi 3, TPU v5p, Trainium 2, Maia 100, MTIA v2). Adding
a chip means adding it to the MCP server's BOM dataset; the agent will pick
it up automatically.

**"Free tier got rate-limited."** — Expected during launch surge. Free tier
is 100 API calls/day = ~10 queries. Pro tier is 10K/hour. We're not making
money on this; the rate limit is just to keep the MCP server reachable.

**"How is this different from Vantage/CloudZero/Kubecost?"** — Those are
backward-looking FinOps on existing bills. This is forward-looking
procurement decision support across multiple clouds plus on-prem, before
you've signed a contract.
