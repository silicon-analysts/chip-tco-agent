# Research Brief: "Chip TCO Comparison Agent" Marquee Notebook for [siliconanalysts.com](http://siliconanalysts.com)

**TL;DR.** This brief specifies a marquee example notebook — a "Chip TCO Comparison Agent" — built on the **raw Anthropic SDK + the official MCP Python SDK** (rather than LangGraph or the Claude Agent SDK), aimed at a Senior ML Infrastructure Engineer at a 30-person AI startup who today does GPU comparison in spreadsheets and getdeploying tabs. The agent takes a workload spec (e.g., *"Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East, 24-month amortization"*), orchestrates 8–12 calls across the six Silicon Analysts MCP tools plus a bundled `cloud_prices.json`, and returns a ranked, provenance-tagged TCO recommendation across cloud (AWS/Azure/GCP/CoreWeave/Lambda) and on-prem options. The proposed $49 / $299 / $999 pricing is directionally right but should likely become $49 / $299 / $1,499 with a free read-only tier; the "aha" is replacing a week of spreadsheet work with a 30-second conversational query. The deliverable below contains Sections A–G plus a fully-populated April 2026 `cloud_prices.json`, a defensible worked example with real benchmarks, the full system prompt draft, and Show HN copy.

---

## Section A — Buyer & Use Case Validation

### Persona — "Maya, Senior ML Infrastructure Engineer at a 30-person AI startup"

The primary buyer is a **Senior ML Infrastructure Engineer at a Series A/B AI startup of 10–50 people**, total comp roughly **$260–$300K** (base $150–$220K + equity), reporting directly to a Head of Engineering, VP Eng, or CTO — there is no "Head of Infra" layer at this size. Daily work blends Kubernetes/Helm/Terraform for GPU nodes, vLLM and TensorRT-LLM tuning, capacity-hunting across **AWS or GCP plus one or two neoclouds (CoreWeave, Lambda, RunPod)**, model-serving SLO enforcement, and FinOps reports for the CFO. A representative job posting ([Character.AI](http://Character.AI), ML Infra) describes the role as *"maximize GPU allocation and utilization for both serving and training,"* which captures the cost-pressure half of the job perfectly.

**Budget authority is the single most important number for our pricing.** Procurement-process surveys converge on a clean three-tier pattern at 10–50 person startups: **under ~$500/mo an IC engineer self-approves on a corporate card**; $500–$2,500/mo requires a Slack-the-CTO conversation; above $2,500/mo triggers a budget review with finance. That makes our $49 tier a no-ask, $299 a "approve before standup," and $999 a real (but easy at this persona's level of GPU spend) procurement event.

A useful secondary persona is the **Staff Platform Engineer at a 100–500-person AI scaleup** with $200K–$2M/mo in GPU spend — same workflow, larger blast radius. Both personas live in the same communities and respond to the same demo.

### The current workflow is genuinely painful — and the pain is well documented

Without a tool like this, Maya spends **3–7 days per major capacity decision** doing the following, all of which surfaced in primary sources:

The default is a spreadsheet. Vantage's homepage tagline is literally *"From spreadsheets to sanity"* — when the FinOps category leader frames the problem this way, it confirms that spreadsheet-driven GPU comparison is endemic, not a strawman. Engineers normalize by hand: [getdeploying.com](http://getdeploying.com) explicitly warns users to *"Compare per-GPU-hour, not per-instance-hour"* because a cheaper 8-GPU instance often costs more per GPU than a single-GPU offering elsewhere. Price spreads are *enormous* and change weekly: getdeploying notes a **96% spread between highest and lowest H100 listings** ($1.25/hr floor vs $14.90/hr ceiling) as of early 2026.

**Build-vs-rent math is opaque and high-stakes.** A widely-cited HN debate (item 36025567) features two senior engineers publicly disagreeing about whether on-prem H100s break even at 8 months or require 25% duty cycle — because nobody has a trustable TCO model. GPUnex's TCO write-up notes that *"Most 'buy vs. rent' analyses only compare hardware price to cloud hourly rate. This dramatically underestimates ownership cost by ignoring electricity, cooling, staff, facility, and depreciation — which together can equal or exceed the hardware cost itself over 3 years."* Above the white space sits **SemiAnalysis's institutional AI Cloud TCO Model**, sold to hyperscalers and funds at rumored $30K–$100K+/yr — the gold standard, but utterly inaccessible to a 30-person startup. That gap is the opportunity.

### The "aha" moment: one sentence in, ranked TCO out

Maya should walk away thinking: *"That just saved me a week of spreadsheet work and probably a $40K mistake."* The headline demo: type *"Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East, 24-month amortization"* and within 30 seconds get a ranked TCO table across hyperscalers, neoclouds, and on-prem, with **$/M-tokens, all-in $/yr, break-even months, and the spec assumptions surfaced for override**. The strongest secondary aha is **the agent volunteering an outside-view fact the user didn't ask for** — e.g., *"Your assumed 80% utilization is unrealistic; production GPU utilization typically averages 35–45%. At 40% utilization, on-prem stops winning until month 22."* That kind of intervention is what made SemiAnalysis famous and is highly defensible because Silicon Analysts' provenance metadata can carry it.

### Pricing — $49 / $299 / $999 is directionally right, with one push-back

Anchoring against the competitive set: **Kubecost Business is $449/mo**, **CloudZero starts at $19 per $1K of AWS spend (~$1,900/mo at $100K spend)**, **Vantage's Pro tier covers up to $7.5K tracked spend**, **SemiAnalysis newsletter is $500/yr** ($42/mo) but the institutional TCO model is institutional-only. Free tools (getdeploying, [computeprices.com](http://computeprices.com), fullstackdeeplearning's `cloud-gpus`) own the bottom.

**$49 Indie:** validated. Below the no-ask threshold, comparable to a SemiAnalysis newsletter sub. Possibly leaving some money on the table at the high end of this tier — but $49 is the right number for the Show HN inbound and for solo founders. *Recommendation: keep $49, add a free read-only tier (3 queries/day) — this is essential for the launch moment.*

**$299 Pro:** validated but tight. Brackets with Vantage Pro and Kubecost Business ($449). At $299 a single ML infra engineer expenses without procurement; one prevented $50K reserved-instance mistake pays for it for ~14 years. *Recommendation: keep, with a clean 14-day trial.*

**$999 Team:** validated and arguably **low**. At a 50–500 person AI scaleup, $999/mo is a CTO rounding error, but at this tier we compete with CloudZero and partial Kubecost deployments. *Recommendation: consider raising to **$1,499/mo** and bundling "1 quarterly model TCO review by a human analyst" — that borrows the SemiAnalysis call playbook and creates a clear premium feel without demanding enterprise sales.*

**Above $999:** custom enterprise, priced as **1–2% of GPU spend** (CloudZero is 1.9%, Vantage Autopilot is 5% of *savings*). For a $5M/yr GPU buyer, 1% = $50K/yr.

**Final tier proposal:** Free (3/day, read-only) → $49 Indie → $299 Pro → $1,499 Team → custom Enterprise.

### How this notebook differentiates from the competitive set

| Competitor | Posture | Why we win in this notebook |
|---|---|---|
| AWS Pricing Calculator / Azure TCO / GCP calc | Single-cloud, manual, no neoclouds, no on-prem | We span 5+ clouds + on-prem in one query |
| Vantage / CloudZero / Cloudability | **Backward-looking** FinOps on existing bills | We are **forward-looking** procurement decision support |
| Kubecost / OpenCost | Monitors what you already run in K8s | We compare options you don't yet own |
| [getdeploying.com](http://getdeploying.com) / [computeprices.com](http://computeprices.com) | Free static comparison tables | We add workload-aware reasoning + on-prem TCO + provenance |
| Shadeform / Thunder Compute / [Vast.ai](http://Vast.ai) | Marketplaces — conflicted as comparison sources | We are vendor-neutral and include them as options |
| SemiAnalysis AI Cloud TCO Model | Authoritative; quarterly Excel; institutional pricing | We are conversational, real-time, and engineer-priced |
| Spreadsheet + 4 sales-rep calls | The status quo | We compress 3–7 days into 30 seconds |

The white space is unambiguous: **engineer-priced, forward-looking, multi-provider + on-prem, conversational**. No tool currently occupies it.

---

## Section B — Technical Architecture

### Framework choice: Raw Anthropic SDK + official MCP Python SDK (with PydanticAI as runner-up)

I evaluated five contenders against the user's stated criteria (familiarity → multi-tool maturity → stability → MCP integration → Anthropic alignment as tiebreaker). The honest scoring as of April 2026:

| Framework | Familiarity to ML infra eng | Multi-tool maturity | 6-mo stability | MCP integration | Verdict |
|---|---|---|---|---|---|
| **Raw Anthropic SDK + `mcp` package** | Highest (everyone has written `messages.create` + tool_use loop) | 3/5 (you write the loop, parallel tool_use is native) | **5/5 — rock-solid semver** | 4/5 (~30 LOC) | **Pick** |
| PydanticAI | Med-High and rising; FastAPI-flavored | 4/5 | 4/5 (Production/Stable since Sep 2025) | **5/5 — cleanest, ~5 LOC** | Strong runner-up |
| LangGraph 1.x | Highest in the survey data; "the" custom agent stack | 5/5 (graph state, HITL, durable, time-travel) | 4/5 (1.0 LTS Oct 2025; one slip in `langgraph-prebuilt 1.0.2`) | 4/5 (`langchain-mcp-adapters`) | Heavy for this; right if branching/HITL needed |
| Claude Agent SDK (Anthropic) | Low; mostly Claude-Code users | 4/5 but biased toward Read/Bash/Edit | **2/5 — still 0.1.x, Alpha PyPI classifier, weekly regressions, *proprietary license*** | 5/5 (in-process SDK MCP servers) | Built for coding agents, not this |
| OpenAI Agents SDK | High (relevant comp) | 5/5 | 4/5 | 5/5 | Wrong vendor for a Claude-first notebook |

**The decisive arguments for raw SDK:**

1. **Aging well.** The `client.messages.create(... tools=...)` surface has been semver-stable since 2024. The notebook will still run unmodified in 12 months. Claude Agent SDK 0.1.x will almost certainly have moved its API by then; LangGraph 1.x will likely look dated as the 2026 industry zeitgeist (visible in LangChain's own blog, MindStudio, LlamaIndex's founder posts) shifts toward minimal SDKs over heavyweight frameworks.
2. **Buyer familiarity is the #1 stated criterion.** Every senior infra engineer has written this loop. Zero new mental model. LangGraph's graph DSL adds friction; Claude Agent SDK's CLI-subprocess architecture is *unfamiliar and surprising* — the wrong vibe for a "look how easy our API is" notebook.
3. **MCP-readability.** Showing how MCP tools are listed → translated to Anthropic tool schema → looped → tool_results returned is *the* canonical educational artifact this notebook should be. Frameworks hide that; the buyer wants to see it once and trust it.
4. **License hygiene.** Claude Agent SDK is governed by Anthropic Commercial Terms, not MIT/Apache. Notebook code gets copy-pasted into products; the raw `anthropic` SDK is unambiguously safe.
5. **Vendor neutrality signal.** Even though Silicon Analysts is Claude-aligned, using the framework that *teaches the protocol* rather than locking to Anthropic's wrapper aligns with the ML-infra audience's anti-lock-in instinct.

**When we'd pick differently:** If we ever need durable long-running workflows with HITL, port to LangGraph using `create_react_agent` + `langchain-mcp-adapters`. If we ship a TypeScript variant of the notebook for the Vercel-leaning audience, Vercel AI SDK 6 is the no-contest choice (it has best-in-class MCP, including OAuth/elicitation in 6.x). Document both as "extensions" in the README.

### Agent topology: single-agent ReAct with explicit plan step

A **single-agent ReAct loop** with a forced **initial planning turn** is the right topology. Justification:

The query is bounded (one workload spec → one ranked recommendation), the tool set is small (6 MCP tools + `cloud_prices.json` lookup + a small computed-cost helper), and there is no need for branching, HITL, or parallel sub-agents. Multi-agent supervisor topologies introduce token overhead (CrewAI measured ~18% over LangGraph) and observability headaches that buy us nothing here. A pure ReAct loop without a planning turn risks the agent firing `get_market_pulse` first and never getting to costing math; an explicit "produce a plan, then execute" prefix solves this cheaply.

The loop runs in a `while` with **a hard cap of 16 model turns**, parallel `tool_use` enabled (Anthropic supports multi-tool-call per turn since 2024), and a final `respond_with_recommendation` synthetic tool that the model is instructed to call last with a Pydantic-validated JSON payload (see Section E for the structured output approach).

### Tool call sequencing — typical 8–12 calls per query

For the canonical query, the expected sequence is:

1. **Plan turn** (no tool call): the model emits a thinking-block plan listing candidate accelerators based on the workload (70B FP8 inference, latency target → H100/H200/B200/MI300X are the natural shortlist).
2. **Parallel batch #1 — `get_accelerator_costs`** for `["H100","H200","B200","MI300X"]` (4 tool calls in one turn). Returns BOM, mfg cost, sell price, memory, FP8 TFLOPS, packaging type, provenance.
3. **`get_market_pulse`** for `["CoWoS-S","HBM3e","Blackwell supply"]` (1 call). Returns curated supply-chain headlines that produce risk flags.
4. **Parallel batch #2 — `get_packaging_costs`** for the packaging types observed in (2) (typically `CoWoS-L`, `HBM stack`) — 1–2 calls. Used for on-prem BOM sanity check and supply-risk reasoning.
5. **`get_hbm_market_data`** (1 call) for current HBM3e pricing trajectory, which feeds the on-prem capex narrative and 2026–27 sensitivity flags.
6. **`calculate_chip_cost`** (0–1 calls) only if the agent needs a derived cost for a chip the user proposed but isn't in the standard table; usually skipped.
7. **`get_wafer_pricing`** (0–1 calls) — generally skipped for an inference TCO question; included only if user asked about manufacturing economics.
8. **Local `lookup_cloud_price` tool** (computed-not-MCP; reads `cloud_prices.json`) — N calls (one per chip × provider combo to consider, ~6–10 calls). Cheap and instantaneous.
9. **Local `compute_tco` helper** (computed) — one final call that takes (chip, qty_gpus, cloud_price OR on_prem_capex, power_kw, util, horizon_months) and returns capex+opex+monthly+amortized.
10. **`respond_with_recommendation`** structured-output call — final turn.

**Target: 5–15 tool calls total**, with steps 2 and 4 batched in parallel for latency. Realistic wall-clock: **30–55 seconds** end-to-end on Sonnet 4.5; **~75–110 seconds** on Opus.

### External data not in the Silicon Analysts API

Three categories of data are not in the API and must be supplied:

**Cloud GPU pricing.** The Silicon Analysts API tracks chip-level economics (BOM, sell price, packaging, HBM), not cloud SKU $/hr. **Recommendation: bundle a `cloud_prices.json` file in the repo with explicit `last_verified` per entry plus a top-level `data_sources` array of source URLs.** Rejected alternatives: (a) scrape at runtime — too brittle, hyperscaler pages change weekly and CSPs rate-limit; (b) make on-prem-only — kills the most valuable comparison; (c) require user to bring their own — kills the 60-second demo. The bundled JSON with a "last verified 2026-04-30" banner in the notebook output is the right tradeoff: honest, reproducible, easy to update, and cleanly separable from the agent code.

**Power/cooling cost assumptions for on-prem TCO.** Bundle a small `onprem_assumptions.json` with conservative defaults: **$0.10/kWh industrial (US avg ~$0.082, Virginia ~$0.08–0.10, sensitivity flag for $0.12–0.15)**, **PUE 1.4 air-cooled / 1.2 liquid-cooled**, **colocation $200/kW/month** (CBRE H2 2025 wholesale primary US avg = $195.94/kW/month for 250–500 kW deployments), liquid CDU surcharge $1,800/mo for B200-class, cross-connects $300/mo, OEM support 7%/yr of capex (8% for Blackwell), staff/SRE 10%/yr, software $1,500/GPU/yr. Source: EIA Electricity Monthly (Apr 2026); CBRE Data Center Report H2 2025; NVIDIA DGX user guides; Supermicro AS-8125GS spec sheets.

**Performance benchmarks (tokens/sec).** Bundle a `perf_benchmarks.json` mapping (chip, model, quant, framework) → (per-GPU aggregate tok/s, per-stream tok/s, ITL ms, source URL, confidence). Defensible numbers for Llama 3.1 70B FP8 are tabulated in Section C.

### Output schema

The agent's final structured output is a Pydantic model the agent must populate via tool call (the `respond_with_recommendation` synthetic tool). Top-level shape:

```
TCORecommendation:
  query_echo: { workload, throughput_target, latency_target, region, horizon_months, budget_cap_usd }
  recommendation:
    rank: 1
    deployment: "cloud" | "on-prem" | "hybrid"
    chip: "H200"
    provider: "CoreWeave"
    sku: "HGX H200 (8x), 3yr reserved"
    qty_gpus: 4
    rationale_short: "Best $/M-tokens at SLA; strongest provenance; not supply-pinned."
  cost_breakdown:
    capex_usd: 0
    opex_monthly_usd: 18170
    opex_24mo_usd: 436080
    amortized_per_M_tokens_usd: 5.98  # at 100M tokens/day (denominator = 72,960 M tokens over 24mo); see Section C convention note
  performance_assumptions:
    per_gpu_tokens_per_sec: 2700  # sustained, FP8, vLLM 0.9, ISL 1024 / OSL 256
    benchmark_source_url: "https://www.coreweave.com/blog/coreweave-delivers-breakthrough-ai-performance..."
    benchmark_confidence_tier: "high"
  alternatives: [TCORecommendation, TCORecommendation]   # 2-3 ranked
  risk_flags:
    - { type: "supply", severity: "medium", description: "...", source_provenance: {...} }
  confidence:
    overall: "high" | "medium" | "low"   # min() of contributing tiers, surfaced in UI as a badge
    contributing_tiers: { accelerator_costs: "high", market_pulse: "medium", cloud_prices: "high (verified 2026-04-30)" }
  reasoning_summary: "3-5 sentences"
  caveats: [ "B200 not yet GA on Lambda Labs as of 2026-04-30 — excluded from comparison" ]
```

`provenance.confidence_tier` from each MCP response is propagated all the way to the user-visible badge: **the `overall` confidence is `min()` over all contributing tiers**. If any input was `low`, the recommendation is presented with a yellow ⚠️ badge and an explicit "low confidence inputs: …" line. This is the single most important design choice for trust — it makes the agent honest about not being smarter than its data.

### The `cloud_prices.json` (April 2026) — fully populated

```json
{
  "as_of": "2026-04-30",
  "currency": "USD",
  "unit": "$/GPU-hour (per single GPU within multi-GPU instance)",
  "data_sources": [
    "https://lambda.ai/pricing",
    "https://www.coreweave.com/pricing",
    "https://aws.amazon.com/ec2/instance-types/p5/",
    "https://aws.amazon.com/ec2/instance-types/p6/",
    "https://aws.amazon.com/ec2/capacityblocks/pricing/",
    "https://instances.vantage.sh/aws/ec2/p5.48xlarge",
    "https://instances.vantage.sh/aws/ec2/p5en.48xlarge",
    "https://instances.vantage.sh/aws/ec2/p6-b200.48xlarge",
    "https://instances.vantage.sh/azure/vm/nd96isrh100-v5",
    "https://cloudprice.net/vm/Standard_ND96isr_MI300X_v5",
    "https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/ndmi300xv5-series",
    "https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/nd-gb200-v6-series",
    "https://cloud.google.com/compute/gpus-pricing",
    "https://docs.cloud.google.com/compute/docs/accelerator-optimized-machines",
    "https://www.networkworld.com/article/4113150/aws-hikes-prices-for-ec2-capacity-blocks-amid-soaring-gpu-demand.html"
  ],
  "global_notes": {
    "reserved_pricing": "AWS, Azure, GCP do not publish flat $/GPU-hr for 1yr/3yr reserved; values shown are computed from public discount tiers (AWS Savings Plans ~25-31%/45%, Azure RIs ~30-35%/45-55%, GCP CUDs ~28-37%/46-55%). Lambda and CoreWeave multi-year reserved are 'contact sales'; only 1-Click Cluster (Lambda) and 'Up to 60% off' Capacity Plans (CoreWeave) are public.",
    "h100_market_state": "AWS p5 dropped 44% in June 2025; H100 is now broadly $2-7/GPU-hr depending on provider tier. Specialized neoclouds (RunPod, Crusoe, Vultr) frequently below $2/GPU-hr.",
    "blackwell_ga_status": "B200 GA on AWS p6-b200 (limited regions), Azure ND-GB200-v6 (GA but not on public PAYG calculator), GCP A4 (reservation-only, no self-serve OD), Lambda (GA), CoreWeave (GA). Supply still constrained; NVIDIA reported ~3.6M-unit backlog in early 2026.",
    "mi300x_provider_coverage": "Only Azure offers MI300X among the five providers. AWS declined publicly (pushes Trainium2). GCP TPU-focused. Lambda and CoreWeave are NVIDIA-only."
  },
  "pricing": {
    "H100": {
      "AWS":      { "instance": "p5.48xlarge",            "gpus_per_instance": 8, "on_demand_per_gpu_hr": 6.88,  "1yr_reserved_per_gpu_hr": 4.75, "3yr_reserved_per_gpu_hr": 3.78, "capacity_block_per_gpu_hr": 3.93, "ga_status": "GA", "last_verified": "2026-04-28", "confidence": "high (OD) / medium (reserved est.)" },
      "Azure":    { "instance": "Standard_ND96isr_H100_v5","gpus_per_instance": 8, "on_demand_per_gpu_hr": 12.29, "1yr_reserved_per_gpu_hr": 8.60, "3yr_reserved_per_gpu_hr": 6.76, "ga_status": "GA", "last_verified": "2026-04-28" },
      "GCP":      { "instance": "a3-highgpu-8g",           "gpus_per_instance": 8, "on_demand_per_gpu_hr": 10.98, "1yr_reserved_per_gpu_hr": 7.69, "3yr_reserved_per_gpu_hr": 4.94, "spot_per_gpu_hr": 2.25, "ga_status": "GA", "last_verified": "2026-04-07" },
      "Lambda":   { "instance": "8x H100 SXM Cloud Instance","gpus_per_instance": 8, "on_demand_per_gpu_hr": 3.99, "1yr_reserved_per_gpu_hr": 5.54, "3yr_reserved_per_gpu_hr": null, "ga_status": "GA", "last_verified": "2026-04-30", "notes": "1-Click Cluster premium >OD because dedicated InfiniBand fabric; multi-yr reserved 'contact sales'." },
      "CoreWeave":{ "instance": "HGX H100 (8x)",            "gpus_per_instance": 8, "on_demand_per_gpu_hr": 6.16, "1yr_reserved_per_gpu_hr": null, "3yr_reserved_per_gpu_hr": 2.46, "ga_status": "GA", "last_verified": "2026-04-30", "notes": "3yr est. at 60% off list per public 'Up to 60%' tier." }
    },
    "H200": {
      "AWS":      { "instance": "p5en.48xlarge",           "gpus_per_instance": 8, "on_demand_per_gpu_hr": 7.91,  "1yr_reserved_per_gpu_hr": 5.46, "3yr_reserved_per_gpu_hr": 4.35, "capacity_block_per_gpu_hr": 5.20, "ga_status": "GA", "last_verified": "2026-04-27" },
      "Azure":    { "instance": "Standard_ND96isr_H200_v5","gpus_per_instance": 8, "on_demand_per_gpu_hr": 13.78, "1yr_reserved_per_gpu_hr": 9.65, "3yr_reserved_per_gpu_hr": 7.58, "ga_status": "GA (limited)", "last_verified": "2026-04-07" },
      "GCP":      { "instance": "a3-ultragpu-8g",          "gpus_per_instance": 8, "on_demand_per_gpu_hr": 10.85, "1yr_reserved_per_gpu_hr": 7.60, "3yr_reserved_per_gpu_hr": 4.88, "spot_per_gpu_hr": 3.72, "ga_status": "GA (limited regions)", "last_verified": "2026-04-07" },
      "Lambda":   { "instance": null, "on_demand_per_gpu_hr": null, "1yr_reserved_per_gpu_hr": null, "3yr_reserved_per_gpu_hr": null, "ga_status": "Not on public self-serve menu (private/reserved deals only)", "last_verified": "2026-04-30" },
      "CoreWeave":{ "instance": "HGX H200 (8x)",            "gpus_per_instance": 8, "on_demand_per_gpu_hr": 6.31, "1yr_reserved_per_gpu_hr": null, "3yr_reserved_per_gpu_hr": 2.52, "ga_status": "GA", "last_verified": "2026-04-30" }
    },
    "B200": {
      "AWS":      { "instance": "p6-b200.48xlarge",        "gpus_per_instance": 8, "on_demand_per_gpu_hr": 14.24, "1yr_reserved_per_gpu_hr": 9.83, "3yr_reserved_per_gpu_hr": 7.83, "capacity_block_per_gpu_hr": 9.36, "ga_status": "GA (limited regions: us-east-1, us-east-2, us-west-2)", "last_verified": "2026-04-29" },
      "Azure":    { "instance": "ND-GB200-v6 / ND-B200-v6", "on_demand_per_gpu_hr": null, "1yr_reserved_per_gpu_hr": null, "3yr_reserved_per_gpu_hr": null, "ga_status": "GA (announced GTC 2025) but not on public PAYG calculator; enterprise contract only", "last_verified": "2026-04-30" },
      "GCP":      { "instance": "a4-highgpu-8g",            "gpus_per_instance": 8, "on_demand_per_gpu_hr": null, "1yr_reserved_per_gpu_hr": null, "3yr_reserved_per_gpu_hr": null, "spot_per_gpu_hr": 6.69, "ga_status": "Reservation-only; no self-serve OD per GCP docs", "last_verified": "2026-04-07" },
      "Lambda":   { "instance": "8x B200 SXM6 Cloud Instance","gpus_per_instance": 8, "on_demand_per_gpu_hr": 6.69, "1yr_reserved_per_gpu_hr": 8.87, "3yr_reserved_per_gpu_hr": null, "ga_status": "GA", "last_verified": "2026-04-30" },
      "CoreWeave":{ "instance": "HGX B200 (8x)",            "gpus_per_instance": 8, "on_demand_per_gpu_hr": 8.60, "1yr_reserved_per_gpu_hr": null, "3yr_reserved_per_gpu_hr": 3.44, "ga_status": "GA", "last_verified": "2026-04-30" }
    },
    "MI300X": {
      "AWS":      { "instance": null, "ga_status": "Not offered — AWS publicly declined (pushes Trainium2)", "last_verified": "2026-04-30" },
      "Azure":    { "instance": "Standard_ND96isr_MI300X_v5","gpus_per_instance": 8, "on_demand_per_gpu_hr": 6.00, "1yr_reserved_per_gpu_hr": 4.20, "3yr_reserved_per_gpu_hr": 3.30, "ga_status": "GA (since Q3 2024)", "last_verified": "2026-04-30", "notes": "OD figure is approximate; trackers conflict ($6 starting tier vs. higher full PAYG)." },
      "GCP":      { "instance": null, "ga_status": "Not offered (TPU-focused)", "last_verified": "2026-04-30" },
      "Lambda":   { "instance": null, "ga_status": "Not on public menu", "last_verified": "2026-04-30" },
      "CoreWeave":{ "instance": null, "ga_status": "Not on public menu (NVIDIA-only fleet)", "last_verified": "2026-04-30" }
    }
  }
}
```

The notebook MUST display the `as_of` and `last_verified` dates prominently and warn the user explicitly when prices are >60 days old.

---

## Section C — Worked Example (End-to-End)

> **Cost-per-million-token convention.** All cost-per-million-token values computed with denominator = `daily_tokens × 30.4 days/month × horizon_months / 1,000,000`. For the headline query (100M tokens/day, 24 months) this denominator is 72,960 million tokens.

**Query.** *"Llama 3.1 70B inference, 100M tokens/day target, p99 latency <500ms, US-East, 24-month amortization, no budget cap"*

### Step 1 — Workload sizing (computed locally before any tool calls)

100,000,000 tokens/day ÷ 86,400 s/day = **1,157 tok/s sustained average**. Applying a **4× diurnal/burst peaking factor** (typical for production inference traffic) → **~5,000 tok/s peak**. The p99 <500 ms target is interpreted as **TTFT for a 1024-token prompt** (the only feasible reading: a strict end-to-end <500 ms for a 256-token output requires <2 ms/token, which no current accelerator delivers at meaningful concurrency for a 70B model — the agent should flag this assumption back to the user).

### Step 2 — Defensible per-GPU throughput (Llama 3.1 70B, FP8, vLLM/TRT-LLM, ISL 1024/OSL 256, concurrency ~50)

| Chip | Per-GPU aggregate tok/s | Per-stream tok/s @ low concurrency | Source | Confidence |
|---|---|---|---|---|
| H100 80GB SXM | **1,800** (range 1,500–2,500) | 53–71 | NVIDIA NIM perf docs; AMD ROCm comparison (MI300-074); MLPerf v4.1 | High |
| H200 141GB SXM | **3,800** (range 3,000–4,500) | 60–75 | MLPerf v5.1 (Krai/Dell SGLang 31,391 / vLLM 30,893 on 8-GPU); CoreWeave MLPerf v5.0 blog | High |
| B200 180GB SXM6 (FP8) | **7,000** (range 6,000–8,500) | 100–150 | Estimated by halving Lambda's MLPerf v5.1 FP4 result (102,725 / 8 / 2). **Flagged medium-confidence — no public B200 FP8 70B benchmark as of Apr 2026.** | Medium |
| B200 180GB SXM6 (FP4) | 12,500 (high-water) | — | Lambda MLPerf v5.1 (8×B200 Llama 2 70B Offline = 102,725 tok/s) | High |
| MI300X 192GB | **2,000** (range 1,500–2,700) | 50–65 | AMD ROCm blog (MI300-074) Llama 3.1 70B FP8 vLLM; arXiv 2510.27583 (independent) shows 37–66% of H100/H200 in real-world | High (range), Medium (point) |

**Sustained throughput = ~70% of peak aggregate** (accounts for tail latency, batch efficiency, headroom for the SLO).

### Step 3 — GPU count to handle 5,000 tok/s peak at p99 <500 ms TTFT

| Chip | Sustained per-GPU tok/s | GPUs for 5,000 tok/s peak | Round to deployable unit | Min HA config |
|---|---|---|---|---|
| H100 | 1,260 | 4.0 | **4** | 4 (½ HGX node) |
| H200 | 2,660 | 1.9 | 2 | **4** (½ node, redundancy) |
| B200 (FP8) | 4,900 | 1.0 | 2 | **2** (TP2, redundancy) |
| MI300X | 1,400 | 3.6 | **4** | 4 (½ node) |

### Step 4 — ReAct trace

```
Thought (turn 1, plan):
  User wants 70B inference, 100M tok/day, p99<500ms, US-East, 24mo, no budget cap.
  Workload class: dense decoder LLM, FP8, latency-sensitive inference.
  Candidate accelerators: H100, H200, B200, MI300X.
  Disqualified: TPU v5p (Llama is not a first-class TPU citizen), Trainium2 (compiler maturity for 70B FP8 still rough), Gaudi3 (limited cloud availability), MI355X (very new, perf data sparse for 70B), MTIA/Maia (not externally rentable).
  Plan: parallel-fetch chip BOMs for the 4 candidates; pull market_pulse for CoWoS/HBM/Blackwell-supply; compute cloud TCO for each (chip, provider) cell; compute on-prem TCO for each chip; rank.

Action (turn 2): parallel batch
  - get_accelerator_costs(chips=["H100"])
  - get_accelerator_costs(chips=["H200"])
  - get_accelerator_costs(chips=["B200"])
  - get_accelerator_costs(chips=["MI300X"])
  - get_market_pulse(topics=["CoWoS-S","HBM3e","Blackwell supply"])

Observation (turn 2): [5 responses]
  H200: { sellPrice: ~$32500, fp8TflopsSparse: 3958, memCapGb: 141, memBwTbS: 4.8, packaging: CoWoS-L,
          provenance: {confidence_tier: "high", last_updated: "2026-04-22"} }
  B200: { sellPrice: ~$50000, fp8TflopsSparse: 9000, memCapGb: 180-192, memBwTbS: 8.0, packaging: CoWoS-L,
          provenance: {confidence_tier: "high"} }
  H100: { sellPrice: ~$27500, fp8TflopsSparse: 1979, memCapGb: 80, memBwTbS: 3.35, packaging: CoWoS-S }
  MI300X: { sellPrice: ~$17500, fp8TflopsSparse: 2615, memCapGb: 192, memBwTbS: 5.325 }
  market_pulse: [
    {headline: "TSMC CoWoS capacity 75-80k wpm Q4-2025, projected 120-130k end-2026; >85% booked", confidence: "high"},
    {headline: "HBM3e contract prices +20% YoY for 2026 deliveries; SK Hynix/Micron sold out CY2026", confidence: "high"},
    {headline: "Blackwell B200 GA broadly but 16-26 wk lead on new HGX systems", confidence: "medium"}
  ]

Thought (turn 3):
  Supply story: HBM and CoWoS are tight; B200 has lead-time risk for on-prem. H100/H200 readily
  available off-lease. This becomes a risk_flag in the output.
  Now pull cloud_prices for each (chip, provider) viable cell.

Action (turn 3): parallel batch — local lookup tool
  - lookup_cloud_price("H100", ["AWS","Azure","GCP","Lambda","CoreWeave"])
  - lookup_cloud_price("H200", ["AWS","Azure","GCP","Lambda","CoreWeave"])
  - lookup_cloud_price("B200", ["AWS","Azure","GCP","Lambda","CoreWeave"])
  - lookup_cloud_price("MI300X", ["AWS","Azure","GCP","Lambda","CoreWeave"])

Observation (turn 3): [4 responses, see cloud_prices.json above]
  Notes: B200 not self-serve OD on Azure/GCP; MI300X only on Azure.
  Lambda H200 not on public menu.

Thought (turn 4):
  For each chip, pick the lowest-cost provider with realistic 24-mo commit (3yr reserved often
  cheaper than 24-mo on-demand; user did not exclude reserved).
  Compute monthly and 24-mo cloud cost for the GPU counts in Step 3.

Action (turn 4): compute_tco helper, parallel for each shortlist
  (per-GPU 3yr reserved $/hr from cloud_prices.json × N_gpus × 730 hr/mo × 24 mo)

Observation (turn 4):
  Cloud option costs (24-mo, 3yr reserved tier, lowest provider per chip):
  H100  × 4 GPUs × CoreWeave $2.46/GPU-hr × 730 × 24 = $172,397
  H200  × 4 GPUs × CoreWeave $2.52/GPU-hr × 730 × 24 = $176,602
  B200  × 2 GPUs × CoreWeave $3.44/GPU-hr × 730 × 24 = $120,538
  MI300X × 4 GPUs × Azure   $3.30/GPU-hr × 730 × 24 = $231,264
  (Lowest-priced 1yr / on-demand cells also computed, omitted for brevity.)

Thought (turn 5):
  On-prem alternative: even at 4 GPUs (½ node) the buyer must purchase a full 8-GPU server.
  At 100M tok/day workload, on-prem economic case is weak: 4 GPUs idle 50% of the time.
  Compute anyway for completeness (using the bundled on-prem assumptions and Section research).

Action (turn 5): compute_tco helper for on-prem
  - on-prem 8x H100, 24mo TCO = ~$377K depreciated capex / $593K cash → $/GPU-hr ≈ $3.16
    Effective for 4 GPUs used = ~$188K
  - on-prem 8x B200, 24mo TCO = ~$624K depreciated → $/GPU-hr ≈ $5.24
    Effective for 2 GPUs used = ~$78K (but pays for 8)
  - on-prem 8x MI300X, 24mo = ~$416K depreciated → $/GPU-hr ≈ $3.49

Observation (turn 5): on-prem only attractive vs cloud at >70% utilization.
  At our 25-30% effective utilization (1,157/5000 sustained vs peak), cloud reserved wins clearly.

Thought (turn 6):
  Rank: B200/CoreWeave 3yr reserved ($120K) is cheapest by absolute cost. But:
  - B200 FP8 70B benchmark has medium confidence (estimated, not measured publicly).
  - Supply lead time 16-26 wk = risk for capacity expansion.
  - SLA at 2 GPUs = no HA; one node failure = outage.
  H200/CoreWeave 3yr reserved ($177K) is +47% cost but:
  - Benchmark confidence high (MLPerf v5.1).
  - 4 GPUs gives meaningful HA headroom.
  - No supply pressure.
  H100/CoreWeave is very close ($172K) and is the most de-risked: best benchmarks, oldest
  tooling, cheapest. The H200 advantage is mostly memory headroom for context length
  growth; the user did not specify long context.
  Recommendation: H100 × 4 on CoreWeave 3yr reserved is the winner on price + de-risk.
  Alternatives: B200 × 2 on Lambda OD (cheapest if you accept the benchmark uncertainty)
  and H200 × 4 on CoreWeave (best for future-proofing context).
  MI300X loses on $/M-tokens at this provider mix; only competitive if user wants vendor
  diversification.

Action (turn 6): respond_with_recommendation(...)
```

### Step 5 — Final structured JSON

```json
{
  "query_echo": {
    "workload": "Llama 3.1 70B inference",
    "throughput_target_tokens_per_day": 100000000,
    "throughput_target_peak_tps": 5000,
    "latency_target_p99_ms": 500,
    "latency_target_interpreted_as": "TTFT for 1024-token prompt (end-to-end <500ms infeasible at meaningful concurrency for 70B; flagged to user)",
    "region": "US-East",
    "horizon_months": 24,
    "budget_cap_usd": null
  },
  "recommendation": {
    "rank": 1,
    "deployment": "cloud",
    "chip": "H100 80GB SXM",
    "provider": "CoreWeave",
    "sku": "HGX H100 (8x), 3-year reserved",
    "qty_gpus": 4,
    "rationale_short": "Lowest-risk, near-lowest absolute cost. High-confidence MLPerf benchmarks; widely available; no CoWoS-S/HBM lead-time risk; sufficient memory headroom at FP8.",
    "cost_breakdown": {
      "capex_usd": 0,
      "monthly_opex_usd": 7184,
      "opex_24mo_usd": 172397,
      "amortized_per_million_tokens_usd": 2.36,
      "assumptions": "4 GPUs × $2.46/GPU-hr × 730 hr/mo × 24 mo. 3yr-reserved tier per cloud_prices.json (last_verified 2026-04-30). Excludes egress, storage, support."
    },
    "performance_assumptions": {
      "per_gpu_tokens_per_sec_sustained": 1260,
      "per_gpu_tokens_per_sec_peak_aggregate": 1800,
      "framework": "vLLM 0.9 / TRT-LLM, FP8, ISL 1024 / OSL 256, concurrency ~50",
      "benchmark_source_url": "https://docs.nvidia.com/nim/benchmarking/llm/latest/performance.html",
      "benchmark_confidence_tier": "high"
    },
    "ha_posture": "4 GPUs across 2 instances minimum; tolerates single-instance failure with degraded p99."
  },
  "alternatives": [
    {
      "rank": 2,
      "deployment": "cloud",
      "chip": "B200 180GB SXM6",
      "provider": "Lambda Labs",
      "sku": "8x B200 SXM6 Cloud Instance, on-demand",
      "qty_gpus": 2,
      "monthly_opex_usd": 9764,
      "opex_24mo_usd": 234374,
      "amortized_per_million_tokens_usd": 3.21,
      "tradeoff": "Highest per-GPU throughput; cheapest absolute if 1yr reserved ($8.87/GPU-hr); enables future scale to FP4 (~12,500 tok/s/GPU). However, B200 FP8 Llama 70B throughput is medium-confidence (no public benchmark as of Apr 2026; estimated by halving FP4 result). Lower HA at 2 GPUs.",
      "confidence_tier": "medium",
      "why_runner_up": "Better future-proofing and FP4 path, but benchmark and supply uncertainty exceed marginal cost savings."
    },
    {
      "rank": 3,
      "deployment": "cloud",
      "chip": "H200 141GB SXM",
      "provider": "CoreWeave",
      "sku": "HGX H200 (8x), 3-year reserved",
      "qty_gpus": 4,
      "monthly_opex_usd": 7358,
      "opex_24mo_usd": 176602,
      "amortized_per_million_tokens_usd": 2.42,
      "tradeoff": "Marginal +2.4% cost vs H100; +110% memory (141GB vs 80GB) buys headroom for longer-context variants or larger batches. Strongest if context length grows beyond 8K or KV-cache pressure becomes binding.",
      "confidence_tier": "high",
      "why_runner_up": "Equally de-risked as H100 but no current binding need for the extra memory at the stated workload."
    }
  ],
  "rejected_options_summary": {
    "MI300X / Azure (3yr reserved, 4 GPUs)": {
      "opex_24mo_usd": 231264,
      "reason_rejected": "+34% cost vs H100 winner; per-GPU FP8 throughput 0.4-0.7× of H100/H200 in independent academic measurement (arXiv 2510.27583); ROCm tooling parity gap remains in 2026."
    },
    "B200 / AWS p6-b200 OD": {
      "opex_24mo_usd": 499042,
      "reason_rejected": "Reserved tiers undocumented; on-demand at $14.24/GPU-hr is uncompetitive."
    },
    "On-prem 8x H100 (24mo amortized)": {
      "opex_24mo_usd": 376574,
      "reason_rejected": "Workload uses only 4 of 8 GPUs sustained; on-prem requires >70% utilization to beat cloud reserved at this scale (per CBRE/QuoteColo norms). User did not signal long-term commitment beyond 24 months."
    },
    "GCP B200 (a4-highgpu-8g)": {
      "reason_rejected": "Reservation-only as of Apr 2026; no self-serve on-demand pricing published."
    },
    "Azure B200 (ND-GB200-v6)": {
      "reason_rejected": "GA but not on public PAYG calculator; enterprise-contract-only as of Apr 2026."
    },
    "Lambda H200": {
      "reason_rejected": "Not on Lambda's public self-serve menu as of 2026-04-30 (private/reserved deals only)."
    }
  },
  "risk_flags": [
    {
      "type": "supply",
      "severity": "medium",
      "description": "TSMC CoWoS-L capacity >85% booked through 2026; HBM3e contract prices +20% YoY. Affects B200 and MI300X capacity expansions; minimal effect on H100 (CoWoS-S, off-lease availability).",
      "source_provenance": "get_market_pulse, confidence_tier: high",
      "affects_recommendation": false,
      "affects_alternatives": ["rank_2_B200"]
    },
    {
      "type": "single_vendor_exposure",
      "severity": "medium",
      "description": "Recommendation locks to NVIDIA + CoreWeave. Mitigation: 3yr reserved with portable workload (vLLM is provider-agnostic). MI300X/Azure is the only NVIDIA-hedge in the shortlist; +34% cost is the hedge premium.",
      "source_provenance": "computed",
      "affects_recommendation": true
    },
    {
      "type": "geopolitical",
      "severity": "low",
      "description": "Jan 2026 BIS rule allows H200/MI325X case-by-case to China (capped 50% volume, 25% USG fee). Could compress US allocation if exports flow OR cause inventory glut if AI OVERWATCH Act passes. Not material to a US-East 24-month reserved buy.",
      "source_provenance": "get_market_pulse, confidence_tier: high",
      "affects_recommendation": false
    },
    {
      "type": "benchmark_uncertainty",
      "severity": "low_for_recommendation_medium_for_alternative",
      "description": "B200 FP8 Llama 3.1 70B per-GPU throughput estimated by halving Lambda's MLPerf v5.1 FP4 result (102,725 tok/s on 8 GPUs). No public B200 FP8 70B benchmark as of 2026-04-30. Verify before committing.",
      "source_provenance": "estimated",
      "affects_alternatives": ["rank_2_B200"]
    },
    {
      "type": "sla_interpretation",
      "severity": "info",
      "description": "User's 'p99 <500ms' was interpreted as TTFT for a 1024-token prompt. End-to-end <500ms for a 256-token output requires <2ms/token, which is infeasible for 70B at production concurrency on any current accelerator. Confirm intended SLA before final commitment."
    }
  ],
  "confidence": {
    "overall": "high",
    "contributing_tiers": {
      "accelerator_costs": "high",
      "market_pulse": "high",
      "cloud_prices": "high (verified 2026-04-30; AWS/Azure/GCP reserved tiers are computed-from-list-discounts, medium)",
      "perf_benchmarks": "high (H100/H200/MI300X), medium (B200 FP8)"
    }
  },
  "reasoning_summary": "At the stated workload (5,000 tok/s peak), H100 × 4 on CoreWeave 3-year reserved delivers the lowest absolute cost ($172K / 24mo, $2.36 per million tokens) with the highest-confidence performance data. B200 × 2 on Lambda is competitive but rests on a medium-confidence FP8 benchmark and offers less HA headroom. H200 × 4 is a +2.4% premium that buys context-length and KV-cache headroom — a sensible upgrade if context growth is anticipated. On-prem and MI300X are dominated at this scale and provider mix.",
  "caveats": [
    "Cloud reserved $/GPU-hr for AWS/Azure/GCP are computed from public discount tiers; exact Pricing-Calculator queries should confirm before contract.",
    "B200 FP8 70B throughput is estimated, not measured.",
    "On-prem TCO assumes $0.10/kWh, PUE 1.4, $200/kW/mo colo; sensitivity-test to $0.12-0.15/kWh given Virginia GS-5 rate transition.",
    "Recommendation does not include data egress, model-storage S3, or observability tooling — typically adds 5–15% to cloud TCO."
  ]
}
```

### Why the runners-up are runners-up (one-liner each)

**B200 / Lambda** loses by inches on cost-confidence-adjusted ranking: the FP8 70B benchmark is an estimate, and 2 GPUs is fragile. **H200 / CoreWeave** loses by inches on absolute cost: the extra memory is real but unused at this workload. **MI300X / Azure** loses on both per-GPU throughput and unit cost. **On-prem** loses because effective utilization is well below the >70% break-even threshold for a 24-month horizon.

---

## Section D — Notebook Structure (Cell by Cell)

### Cell-by-cell outline

1. **Markdown intro** — one paragraph: what this notebook does, the marquee query example, a screenshot of the final ranked recommendation. Title: *"Chip TCO Comparison Agent — Llama 70B inference, in 30 seconds."*
2. **Setup** — `%pip install anthropic mcp pydantic rich` and a `from rich.console import Console`. No LangChain, no LangGraph, no extra weight.
3. **API key config** — `ANTHROPIC_API_KEY` and `SILICON_ANALYSTS_API_KEY` from env or `getpass`. Free-tier note: *"100 calls/day; one query uses ~10 calls — start here."*
4. **MCP client init** — connect to `https://mcp.siliconanalysts.com` with bearer auth, `await client.list_tools()`, print the 6 tools to confirm. ~10 lines.
5. **Tool adapter** — translate MCP tool schemas to Anthropic `tools=[…]` format; ~15 lines, fully visible (this is the marquee teaching moment).
6. **Local helpers** — `lookup_cloud_price(chip, providers)` reading `cloud_prices.json`; `compute_tco(...)` doing the arithmetic. ~30 lines, side-by-side with MCP tools in the same `tools` array.
7. **System prompt** — the full prompt from Section E, rendered in a markdown cell so it's readable.
8. **Agent loop** — one function `run_agent(query)` with the ReAct loop, parallel tool dispatch, 16-turn cap, structured-output forced via `respond_with_recommendation` synthetic tool. ~50 lines.
9. **The headline query** — `run_agent("Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East, 24-month amortization, no budget cap")`. Render output with `rich` as a ranked table + risk badges + confidence chips.
10. **Three more queries** in subsequent cells: training (8B fine-tune over 1B tokens, budget $50K), edge inference (7B model, 10ms TTFT, EU region), heterogeneous batch (mixed Llama + image gen).
11. **"What to try next"** — 5 prompts to try, instructions to swap in your own `cloud_prices.json`, link to `/integrations` guides, link to upgrade Pro tier.
12. **Footer** — license (MIT), data freshness banner, link to GitHub issue tracker.

### Repo structure

```
chip-tco-agent/
├── [README.md](http://README.md)                  # Quickstart, screenshot, "60 seconds" instructions
├── chip_tco_agent.ipynb       # The marquee notebook
├── chip_tco_[agent.py](http://agent.py)          # Same logic, runnable as a CLI
├── pyproject.toml             # Dependencies pinned
├── cloud_prices.json          # April 2026 snapshot (Section B)
├── onprem_assumptions.json    # $/kWh, PUE, colo, etc.
├── perf_benchmarks.json       # Per-chip Llama 70B FP8 tok/s with sources
├── examples/
│   ├── 01_70b_[inference.py](http://inference.py)    # The headline query
│   ├── 02_8b_[finetune.py](http://finetune.py)
│   ├── 03_edge_[inference.py](http://inference.py)
│   ├── 04_mixed_[workload.py](http://workload.py)
│   └── 05_buy_vs_[rent.py](http://rent.py)
├── .env.example
└── LICENSE                    # MIT
```

### The "60-seconds-to-running" experience — exactly 5 commands

```
git clone https://github.com/silicon-analysts/chip-tco-agent
cd chip-tco-agent
cp .env.example .env  # paste ANTHROPIC_API_KEY and SILICON_ANALYSTS_API_KEY
uv sync
uv run python chip_tco_[agent.py](http://agent.py) "Llama 3.1 70B inference, 100M tokens/day, US-East, 24mo"
```

The README must show this 5-line block in the top 200 pixels, before any prose.

### Pitfalls to avoid (most likely first-user breakage)

The single most likely failure is **Anthropic API key not set / rate-limited at free tier**, which produces a 401 / 429. Wrap the first call in a try/except that prints a friendly diagnostic with the env-var name and a link to [console.anthropic.com](http://console.anthropic.com). Second most likely: **MCP server unreachable** (corporate proxy, expired token); detect by timing out `list_tools()` after 10 s and printing a curl reproduction command. Third: the agent **forgets to call `respond_with_recommendation`** on the final turn — prevent by setting `tool_choice={"type": "tool", "name": "respond_with_recommendation"}` on the last turn after a hard turn cap. Fourth: **stale `cloud_prices.json`** — print a yellow banner if `as_of` is more than 60 days old. Fifth: **prompt brittleness on edge queries** — the system prompt explicitly handles "no chip matches" and "out-of-scope workload" with two few-shot examples (see Section E).

---

## Section E — Prompt Engineering for the Agent

### Tool selection guidance, hallucination bounding, and uncertainty surfacing

The system prompt enforces five hard rules: **(1)** prefer `get_accelerator_costs` for any chip in the 13-chip list and only call `calculate_chip_cost` if the user asks about a chip *not* in the list (e.g., a hypothetical or competitor chip); **(2)** never invent a benchmark, price, or supply-chain claim — if a tool returns null or empty, mark that branch `unknown` and exclude from the ranking with an explicit `caveats` entry; **(3)** propagate `provenance.confidence_tier` from every MCP response, and the final `recommendation.confidence.overall` is the `min()` over all contributing tiers; **(4)** structured output is enforced by the `respond_with_recommendation` synthetic tool with a strict JSON schema (Pydantic-validated client-side) — no free-form final answer is accepted; **(5)** the agent must restate the user's query verbatim in `query_echo`, including any interpretations made (e.g., the p99 latency reading), so the user can correct.

For tool selection, the prompt includes a one-line decision tree per tool. For missing data, the prompt includes one few-shot example of "user asked about Cerebras WSE-3 → not tracked → respond gracefully with `out_of_scope` field listing the request and offering tracked alternatives." For hallucination bounding, the prompt forbids producing any `$/hr`, `tok/sec`, or supply-claim that did not originate from a tool call, and forbids any `confidence_tier: high` output if any input was `medium` or `low`.

### Output-format enforcement: structured tool use beats free-form JSON

**Recommended approach: structured output via a synthetic tool call.** The agent has a final-only tool `respond_with_recommendation(payload: TCORecommendation)` whose schema is the Pydantic model in Section B. On the last turn (turn 16, or earlier when the agent has enough info), `tool_choice` is set to `{"type": "tool", "name": "respond_with_recommendation"}`, forcing the model to emit valid JSON or fail loudly. We validate client-side with Pydantic and retry once with the validation error appended to the conversation if it fails. This is more robust than (a) prompting for JSON and parsing (occasional schema drift), (b) `response_format="json"` (Anthropic doesn't support this for arbitrary schemas), or (c) few-shot only (drifts at long context).

### Full proposed system prompt (drop-in)

```
You are the Silicon Analysts Chip TCO Agent. Your job is to take a workload spec
from an ML infrastructure engineer and return a ranked, defensible recommendation
of accelerator + provider + commitment-term, across cloud and on-prem options.

# AVAILABLE TOOLS

You have access to two classes of tools:

(1) Silicon Analysts MCP tools (authoritative for chip-level economics):
  - get_accelerator_costs(chips): BOM, sell price, gross margin, FP8/BF16 TFLOPS,
    memory, packaging, interconnect for any of the 13 tracked chips
    (H100, H200, B100, B200, GB200, MI300X, MI355X, Gaudi 3, TPU v5p, Trainium 2,
    Maia 100, MTIA v2). PREFER THIS over calculate_chip_cost when the chip is in
    the tracked list.
  - calculate_chip_cost(spec): derive a cost for a chip NOT in the tracked list.
    Use ONLY when the user asks about an untracked chip (e.g., a competitor chip,
    a hypothetical, or a future SKU).
  - get_hbm_market_data(): HBM3/3e/4 pricing, allocation, supplier shares.
  - get_market_pulse(topics): curated supply-chain headlines. Use to derive
    risk_flags, NEVER to source numerical claims.
  - get_wafer_pricing(node, foundry): 300mm wafer prices. Generally not needed
    for inference TCO; use only for build-cost-of-silicon questions.
  - get_packaging_costs(type): CoWoS-S/L, EMIB, SoIC, InFO-PoP, FC-BGA, FC-CSP,
    HBM stack pricing. Use to validate on-prem BOM and surface packaging-supply
    risk.

(2) Local tools (bundled with the notebook):
  - lookup_cloud_price(chip, providers): returns current $/GPU-hr (on-demand,
    1yr-reserved, 3yr-reserved) for a chip across providers from a JSON snapshot.
    Snapshot date is in the response; warn the user if older than 60 days.
  - compute_tco(deployment, chip, qty_gpus, price_per_gpu_hr OR capex_usd,
    power_kw, util, horizon_months): returns cost_breakdown.
  - respond_with_recommendation(payload): your FINAL answer. Always call this
    last. Schema is enforced; schema-invalid output will be rejected and you
    will be asked to retry.

# REASONING STYLE

1. PLAN FIRST. On your first turn, emit a brief plan in plain text: candidate
   accelerators (typically a shortlist of 3-5 from the tracked 13), the data
   you need to fetch, and the comparison axes. Disqualify accelerators that
   are obviously wrong for the workload (e.g., TPU v5p for a Llama 70B job
   the user wants to keep portable) with a one-line reason each.
2. BATCH PARALLEL CALLS. Whenever multiple tool calls are independent, emit
   them in a single turn. Aim for 5-15 total tool calls per query.
3. COMPUTE EXPLICITLY. Show your arithmetic for tokens/sec sizing, GPU count,
   monthly cost, and amortization. Use the perf_benchmarks.json values; never
   invent throughput.
4. RANK THEN JUSTIFY. Pick a #1 and 2-3 alternatives. The #1 is not always the
   cheapest — it's the best risk-adjusted choice. Surface the tradeoff.
5. ALWAYS RESPOND VIA respond_with_recommendation. No prose final answer.

# HARD RULES (DO NOT VIOLATE)

- DO NOT invent prices, throughput numbers, latency numbers, or supply claims.
  Every numerical claim in your output MUST trace to a tool response. If a tool
  returns null/empty for a branch, mark that branch as excluded with a caveat
  and continue with the remaining branches.
- DO NOT label a recommendation `confidence: high` if any contributing input
  was `medium` or `low`. Overall confidence = min(contributing tiers).
- DO NOT exceed 16 reasoning turns. If you reach turn 14, your next action
  MUST be respond_with_recommendation with whatever you have, including
  partial caveats.
- DO NOT recommend an option whose ga_status is "Not offered" or "Not on public
  menu" without explicitly flagging this and why the user might still pursue it
  (e.g., enterprise contract).
- DO NOT silently re-interpret the user's SLA. If you read "p99 <500ms" as
  TTFT-only because end-to-end is infeasible, say so in latency_target_interpreted_as
  AND in caveats.

# HANDLING MISSING DATA

- Chip not in the tracked 13: respond with an `out_of_scope` block listing the
  requested chip and the closest 2 tracked alternatives, plus an explanation
  (e.g., "Cerebras WSE-3 is not tracked; the closest comparison points in our
  dataset are GB200 NVL72 for training and TPU v5p for fixed-graph inference").
- Provider not in cloud_prices.json: state which providers ARE compared and
  invite the user to extend the JSON.
- All four candidate accelerators return null in some critical field: respond
  with confidence: low, recommend the user contact Silicon Analysts for a
  deeper analysis, and exit gracefully.

# OUTPUT FORMAT

Your final answer is one and only one call to respond_with_recommendation with
this payload structure (Pydantic-validated):

{
  query_echo: { workload, throughput_target, latency_target_p99_ms,
                latency_target_interpreted_as, region, horizon_months,
                budget_cap_usd },
  recommendation: { rank: 1, deployment, chip, provider, sku, qty_gpus,
                    rationale_short, cost_breakdown, performance_assumptions,
                    ha_posture },
  alternatives: [ { rank: 2, ... }, { rank: 3, ... } ],   // 2-3 entries
  rejected_options_summary: { "<option>": { opex_24mo_usd, reason_rejected } },
  risk_flags: [ { type, severity, description, source_provenance,
                  affects_recommendation, affects_alternatives } ],
  confidence: { overall: high|medium|low, contributing_tiers: { ... } },
  reasoning_summary: "3-5 sentences",
  caveats: [ ... ]
}

# FEW-SHOT TONE EXAMPLES

(1) When data is solid:
  "H100 × 4 on CoreWeave 3yr reserved at $2.46/GPU-hr is the lowest-risk choice.
   MLPerf-grade benchmarks (high confidence), no supply lead-time risk, sufficient
   FP8 memory headroom. Cost: $172K over 24 months."

(2) When data is sparse:
  "B200 FP8 throughput on Llama 3.1 70B is estimated by halving Lambda's MLPerf
   v5.1 FP4 result; no public FP8 benchmark exists as of 2026-04-30. Treat the
   per-GPU 7,000 tok/s as medium-confidence; verify before committing."

(3) When out of scope:
  "The Cerebras WSE-3 is not in our tracked accelerator set. For wafer-scale
   inference workloads, the closest tracked comparison is GB200 NVL72 (rack-scale
   coherent memory). For dense-decoder LLM inference at this scale, a GPU-cluster
   answer (H100/H200/B200) typically dominates on $/M-tokens; we recommend that
   path unless you have a specific Cerebras commitment."

Begin.
```

---

## Section F — Distribution & Marketing Assets

### Show HN title options (≤80 chars, tested against Show HN norms — concrete, no superlatives)

1. *Show HN: Chip TCO agent — describe a workload, get a ranked GPU recommendation* (78)
2. *Show HN: An MCP agent that compares H100, H200, B200, MI300X TCO in 30 seconds* (78)
3. *Show HN: Replace your GPU pricing spreadsheet with a Claude MCP agent* (69)
4. *Show HN: Llama-70B TCO across AWS, GCP, CoreWeave, Lambda + on-prem, in one query* (80)
5. *Show HN: Open-source notebook — agentic GPU TCO with provenance and confidence tiers* (80)

**My pick: #2.** It's the most specific, names recognizable chips, and uses "MCP agent" which is an SEO/zeitgeist term in 2026 without being overhyped. #3 is the strongest emotional pitch but reads marketing-ish; #2 reads like an engineer wrote it.

### Headline screenshot (the one image)

A two-pane terminal screenshot. **Left pane:** the user types `chip-tco "Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East, 24mo"`. **Right pane:** the rendered ranked table — three rows (H100/CoreWeave winner, B200/Lambda runner-up, H200/CoreWeave third), with `$/M tokens`, `24-month $`, `confidence` chips (green/yellow), and one risk-flag badge ("CoWoS-L supply medium" on the B200 row). At the bottom, a single line: `8 MCP tool calls · 31 seconds · $0.18 in Sonnet 4.5 tokens`. That last line is the kill shot — it makes the entire pitch defensible.

### The 30-second demo (second-by-second)

**0:00–0:03** Title card: *"Chip TCO Comparison Agent — open-source notebook."* **0:03–0:08** Screen recording: user types the headline query at a CLI prompt. **0:08–0:18** ReAct trace streams in real-time — viewer sees `get_accelerator_costs(...)`, `get_market_pulse(...)`, `lookup_cloud_price(...)` flying by, all timestamped. **0:18–0:25** The ranked table renders with the three options, $/M-tokens, confidence chips. **0:25–0:28** Cursor highlights the risk flag and the `last_verified: 2026-04-30` provenance line. **0:28–0:30** End card: *"github.com/silicon-analysts/chip-tco-agent · [siliconanalysts.com](http://siliconanalysts.com)"* with the 5-line clone-and-run snippet underneath.

### Show HN post body (draft)

> **Show HN: An MCP agent that compares H100/H200/B200/MI300X TCO in 30 seconds**
>
> Hi HN — we built a small open-source notebook that takes a workload spec like *"Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East, 24-month amortization"* and returns a ranked TCO recommendation across AWS, Azure, GCP, CoreWeave, Lambda, and on-prem. It's a single-agent ReAct loop on the raw Anthropic SDK, calling six MCP tools we maintain (per-chip BOM, packaging costs, HBM market data, supply-chain pulse, wafer pricing, derived cost helpers) plus a bundled `cloud_prices.json` snapshot dated 2026-04-30 with explicit `last_verified` per row.
>
> The thing we tried hardest to get right is honesty about confidence. Every API response carries `provenance.{source_type, confidence_tier, last_updated}`, and the agent's final recommendation surfaces `min()` of those tiers as a badge. If we don't have a public B200 FP8 70B benchmark — which we don't, as of April 30 — the agent says so and tags that branch as `medium` confidence rather than inventing a number. We think this matters because we've all seen agentic FinOps demos that confidently invent prices.
>
> We'd love feedback on three things: (1) is the worked example (Llama 70B, 5 providers + on-prem) defensible to people who actually buy this hardware? (2) we picked raw Anthropic SDK + the official MCP package over LangGraph and the Claude Agent SDK for stability and readability — would you have picked differently? (3) the bundled `cloud_prices.json` is the part most likely to rot — are you OK with it as a snapshot with a freshness banner, or would you rather scrape at runtime? Repo and notebook in the comments.

### Receptive communities (specific)

- **Subreddits:** r/LocalLLaMA (highest signal — ~3M members, weekly GPU/cost threads), r/MachineLearning, r/MLOps, r/LangChain, r/LLMDevs, r/devops, r/kubernetes, r/aws, r/googlecloud, r/AZURE, r/sysadmin (homelab/colo crowd).
- **Discords / Slacks:** **MLOps Community Slack** (~25K, weekly "what GPU should I rent" threads — *the* highest-conversion channel), **CNCF/Kubernetes Slack** (#kubecost, #wg-batch), **FinOps Foundation Slack**, **vLLM/SGLang/Ray/TGI Discords**, **HuggingFace Discord**, **EleutherAI Discord**, **LocalLLaMA Discord**, plus **CoreWeave/Lambda/RunPod customer Discords**.
- **Newsletters:** SemiAnalysis (Dylan Patel — the anchor), Latent Space (swyx — directly serves this audience), The Pragmatic Engineer (Gergely Orosz), Import Ai (Jack Clark), [MLOps.community](http://MLOps.community) newsletter, TLDR AI, Last Week in AI.
- **X/Twitter:** @dylan522p, @soumithchintala, @swyx + @latentspacepod, @Tim_Dettmers, @karpathy (signal amplifier), @charles_irl (Modal/full-stack-deeplearning), @vipulved (Together), @StasBekman, the official accounts of CoreWeave, Lambda, RunPod, Crusoe, Nebius, Together, Modal, Anyscale, Fireworks, Baseten.
- **Conferences:** KubeCon FinOps Day, Ray Summit, AI Engineer Summit, MLOps World, PyTorch Conference.

### Companion blog post (`/blog/engineering`)

**Title.** *"We built a chip-TCO agent on raw Anthropic SDK + MCP — here's why we skipped LangGraph and the Claude Agent SDK"*

**Outline (3 paragraphs).**

*Para 1 — The problem and the artifact.* Open with the spreadsheet pain: 96% spread on H100 list prices, weekly drift, on-prem TCO routinely undercosted by 50%. Show the headline screenshot (the two-pane terminal). Explain the artifact in two sentences: open-source notebook, six MCP tools + bundled `cloud_prices.json`, headline query runs in 31 seconds and 8 tool calls.

*Para 2 — Why raw SDK won the framework bake-off.* Walk through the honest scoring: LangGraph 1.x is excellent for branching/HITL but adds an abstraction tax we don't need; Claude Agent SDK is built for coding agents (Read/Bash/Edit), still 0.1.x with an Alpha PyPI classifier and a proprietary license; PydanticAI is the strongest dark horse and is the runner-up we ship in `examples/` for readers who prefer it. The decisive criterion was "every senior infra engineer has already written a `messages.create` + tool_use loop" — zero new mental model is the right tax for a marquee notebook.

*Para 3 — The provenance discipline (and what's still hard).* Show the `confidence_tier: min()` propagation rule. Be honest: the hardest part was admitting we don't have a public B200 FP8 70B benchmark, and the right thing to do is tag it medium and let the user decide, not invent a halved-FP4 number and pretend. Close with the open question we want HN feedback on: snapshot `cloud_prices.json` vs. runtime scraping. CTA: clone the repo, try the headline query, open an issue with the `cloud_prices.json` cell that's wrong for your region.

---

## Section G — Pre-Launch Validation

### The 60-second test

Hand the repo URL to a **Senior ML Infra Engineer who has never seen Silicon Analysts** and watch over their shoulder. **Failure modes to pre-empt:** (1) `ANTHROPIC_API_KEY` not set produces an opaque 401 — wrap with a friendly diagnostic; (2) `uv` not installed — provide a `pip install` fallback in the README; (3) MCP server unreachable behind corporate proxy — print a curl reproduction; (4) free-tier rate limit hit on second query — surface remaining-quota in every response and warn at 80%; (5) Python <3.10 — pyproject.toml requires-python >=3.10 with a clear error.

### The "is this real" test (hyperscaler ML engineer scrutiny)

Walk a current Meta/Anthropic/OpenAI ML infra engineer through the worked example and watch for nodding vs. eye-rolling. **The numbers most likely to draw scrutiny and our defenses:** H100 1,800 tok/s/GPU per-GPU sustained (defended by NVIDIA NIM perf docs + AMD MI300-074 cross-publication of the same number for H100); H200 3,800 (defended by MLPerf v5.1 SGLang result of 31,391 on 8 GPUs); **B200 7,000 FP8 — this one will get pushback** (defended honestly: estimated by halving the Lambda MLPerf v5.1 FP4 result, tagged medium-confidence in the output); CoreWeave 3yr reserved $2.46/GPU-hr (defended by CoreWeave's published "Up to 60% off list" + $6.16 OD list); on-prem $377K/24mo for an 8x H100 node (defended by capex + EIA $0.10/kWh + CBRE $200/kW/mo + 7%/yr OEM support — every line item sourced).

The single biggest credibility risk is **claiming a B200 number we can't source**. The defense is being explicit and conservative — and recommending H100 as the winner partly *because* the B200 path has benchmark uncertainty.

### Performance target — under 60 seconds end-to-end

**Target: <45s p50, <60s p99** for the headline query. Wall-clock budget on Sonnet 4.5: planning turn ~3s; parallel batch of 4 `get_accelerator_costs` + 1 `get_market_pulse` ~6s (network-bound, MCP server side); local `lookup_cloud_price` parallel 4-way ~1s; `compute_tco` parallel ~1s; final `respond_with_recommendation` turn ~5s; plus Sonnet thinking time across ~6 turns ~15–25s. Realistic total: **30–55s on Sonnet 4.5; 75–110s on Opus**. Recommend Sonnet 4.5 as the default; let users opt into Opus via env var for harder queries.

### Cost to run (Anthropic-side per query)

System prompt ~2,200 tokens. Tool schemas + JSON schema for `respond_with_recommendation` ~1,500 tokens (sticky in cache). Per-turn tool responses ~500 tokens × 8 turns = 4,000 input tokens cumulative. Final structured output ~1,200 output tokens. Total: **~10K input tokens, ~3K output tokens per query**.

| Model | Input ($/MTok) | Output ($/MTok) | Cost per query |
|---|---|---|---|
| Claude Sonnet 4.5 | $3 | $15 | ~$0.075 |
| Claude Opus 4.x | $15 | $75 | ~$0.375 |

With prompt caching enabled (the 2.2K system prompt is sticky), Sonnet drops to **~$0.04 per query** after the first call — a useful number for the README and the screenshot footer ("$0.04 in Sonnet tokens"). At scale: 1,000 queries/day on Sonnet ≈ $40/day Anthropic cost — well-supported by even the $49 Indie tier.

### Failure modes (rate limits, empty returns, unfulfillable queries)

**API rate limit (429).** Bearer free tier is 100 calls/day; one query = ~10 calls. Surface remaining-quota counter in every response; show a warning at 80% consumed; suggest Pro upgrade at 100% with a deep link. On 429, fail gracefully with a "we hit your free-tier rate limit" message including a `Retry-After` countdown. **Empty tool returns.** If `get_accelerator_costs` returns `null` for a chip, mark that branch excluded; if all four return null, escalate to confidence:low and offer a human-analyst handoff CTA. **Unfulfillable queries** (e.g., "I want sub-millisecond latency for Llama 70B"): the agent's hard rule is to interpret the SLA, flag it explicitly in `latency_target_interpreted_as`, and proceed with the closest feasible interpretation — never silently relax the SLA. **Conflicting tool data** (e.g., MCP says CoWoS-L pricing $X, packaging tool says $Y): surface both, take the more recent `last_updated`, and add a `caveats` entry. **Network flakiness on the MCP server**: 10s timeout per call, 1 retry, then fail the branch with explicit caveat — never silently drop a branch.

---

## Conclusion

This brief specifies an opinionated, defensibly-real marquee notebook: **raw Anthropic SDK + MCP** for the framework, **single-agent ReAct with a forced plan turn** for topology, **bundled `cloud_prices.json` with explicit freshness** for the data gap, and **confidence-tier propagation as the trust contract** with the user. The worked Llama-70B example holds up: H100 × 4 on CoreWeave 3yr reserved wins on risk-adjusted cost ($172K / 24mo, $2.36 per million tokens), with B200 × 2 on Lambda as the future-proofing alternative whose only weakness is an honestly-flagged FP8 benchmark gap. The pricing structure ($49 / $299 / $1,499 + free read-only + custom Enterprise) is calibrated against real comparables (SemiAnalysis newsletter $42/mo, Vantage Pro at the $299 anchor, CloudZero ~$1,900 floor, SemiAnalysis institutional $30K+ ceiling). The deeper insight: the artifact's most differentiated feature isn't the cost math — it's the propagation of `provenance.confidence_tier` from every API response into a user-visible badge that admits when we don't know. That admission is what separates this from the agentic-FinOps demos that invent confident numbers and from SemiAnalysis spreadsheets that hide their assumptions, and it's the line the Show HN post should lead with.
