"""
Chip TCO Comparison Agent — single-file implementation.

Takes a workload specification (e.g., "Llama 3.1 70B inference, 100M tokens/day,
p99 <500ms, US-East, 24mo") and returns a ranked TCO recommendation across cloud
providers and on-prem options.

Architecture (see docs/design.md for the long version):
  - Raw Anthropic SDK + official MCP Python SDK (no LangGraph, no Claude Agent SDK).
  - Single-agent ReAct loop with a forced initial planning turn and a 10-turn cap.
  - 6 MCP tools (Silicon Analysts API) + 3 local tools (cloud price lookup,
    TCO arithmetic, structured-output sink).
  - Final output is forced via the `respond_with_recommendation` synthetic tool,
    Pydantic-validated client-side; one validation retry on failure.
  - Confidence-tier propagation: `confidence.overall = min(contributing_tiers)`
    is enforced in code after the agent returns, even if the model claims higher.

The notebook (chip_tco_agent.ipynb) and examples/*.py both import from this
module; do not duplicate agent logic elsewhere.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from contextlib import asynccontextmanager
from datetime import date
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

# anthropic and mcp are imported lazily inside the functions that use them so
# that the data-only surface (Pydantic schemas, local tool helpers, confidence
# propagation, rendering) is importable without those heavier dependencies.
if TYPE_CHECKING:
    import anthropic
    from mcp import ClientSession


# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
CLOUD_PRICES_PATH = REPO_ROOT / "cloud_prices.json"
ONPREM_PATH = REPO_ROOT / "onprem_assumptions.json"
PERF_PATH = REPO_ROOT / "perf_benchmarks.json"

DEFAULT_MCP_URL = "https://siliconanalysts.com/api/mcp"
DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TURNS = 10
# When the agent reaches this turn (0-indexed), force respond_with_recommendation.
# Spec says force at turn 14 with a 16-turn cap (ratio 7/8); we apply the same
# ratio to our 10-turn cap → force at turn 8.
FORCE_RESPOND_AT_TURN = 8

LIST_TOOLS_TIMEOUT_S = 10.0
DEFAULT_REQUEST_MAX_TOKENS = 4096
STALENESS_THRESHOLD_DAYS = 60

# Anthropic pricing (per million tokens). Used only for the cost-tracking footer.
MODEL_PRICING = {
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-7": {"input": 3.0, "output": 15.0},
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
}


# ----------------------------------------------------------------------------
# Pydantic schemas — TCORecommendation
#
# Matches the shape in spec Section B and the worked example in Section C Step 5.
# Fields are typed strictly where the spec is closed (deployment, confidence
# tiers) and as plain str where the spec leaves them open (severity values like
# "low_for_recommendation_medium_for_alternative" appear in the worked example).
# ----------------------------------------------------------------------------

class ConfidenceTier(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Deployment(str, Enum):
    CLOUD = "cloud"
    ONPREM = "on-prem"
    HYBRID = "hybrid"


TIER_RANK = {
    ConfidenceTier.LOW: 0,
    ConfidenceTier.MEDIUM: 1,
    ConfidenceTier.HIGH: 2,
}


class CostBreakdown(BaseModel):
    capex_usd: float = 0.0
    monthly_opex_usd: float | None = None
    opex_24mo_usd: float | None = None
    opex_horizon_usd: float | None = None
    amortized_per_million_tokens_usd: float | None = None
    assumptions: str | None = None

    model_config = ConfigDict(extra="allow")


class PerformanceAssumptions(BaseModel):
    per_gpu_tokens_per_sec_sustained: float | None = None
    per_gpu_tokens_per_sec_peak_aggregate: float | None = None
    framework: str | None = None
    benchmark_source_url: str | None = None
    benchmark_confidence_tier: ConfidenceTier | None = None

    model_config = ConfigDict(extra="allow")


class Option(BaseModel):
    """One ranked option (recommendation #1 or an alternative)."""

    rank: int
    deployment: Deployment
    chip: str
    provider: str
    sku: str
    qty_gpus: int
    rationale_short: str | None = None
    cost_breakdown: CostBreakdown
    performance_assumptions: PerformanceAssumptions | None = None
    ha_posture: str | None = None
    # Alternative-only fields (per spec Section C Step 5):
    tradeoff: str | None = None
    why_runner_up: str | None = None
    confidence_tier: ConfidenceTier | None = None

    model_config = ConfigDict(extra="allow")


class RejectedOption(BaseModel):
    opex_24mo_usd: float | None = None
    reason_rejected: str

    model_config = ConfigDict(extra="allow")


class RiskFlag(BaseModel):
    type: str
    severity: str  # spec uses values like "low", "medium", "info", and freeform strings
    description: str
    source_provenance: str | None = None
    affects_recommendation: bool | None = None
    affects_alternatives: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class Confidence(BaseModel):
    overall: ConfidenceTier
    contributing_tiers: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class QueryEcho(BaseModel):
    workload: str
    throughput_target_tokens_per_day: int | None = None
    throughput_target_peak_tps: float | None = None
    latency_target_p99_ms: int | None = None
    latency_target_interpreted_as: str | None = None
    region: str | None = None
    # `horizon_months` is the normalized number used for math; `horizon_original`
    # preserves the user's phrasing (e.g., "30 days", "24 months", "3 years")
    # so the renderer can display "30 days" instead of the misleading "1 months".
    horizon_months: int | None = None
    horizon_original: str | None = None
    budget_cap_usd: float | None = None

    model_config = ConfigDict(extra="allow")


class TCORecommendation(BaseModel):
    query_echo: QueryEcho
    recommendation: Option
    alternatives: list[Option] = Field(default_factory=list)
    rejected_options_summary: dict[str, RejectedOption] = Field(default_factory=dict)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    confidence: Confidence
    reasoning_summary: str
    caveats: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


# ----------------------------------------------------------------------------
# Run metrics — tracked through the loop, displayed in the footer
# ----------------------------------------------------------------------------

class RunMetrics(BaseModel):
    turns: int = 0
    tool_calls: int = 0
    mcp_tool_calls: int = 0
    local_tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    elapsed_seconds: float = 0.0
    model: str = DEFAULT_MODEL

    def estimated_cost_usd(self) -> float:
        rates = MODEL_PRICING.get(self.model, MODEL_PRICING[DEFAULT_MODEL])
        return (
            self.input_tokens / 1_000_000 * rates["input"]
            + self.output_tokens / 1_000_000 * rates["output"]
        )


# ----------------------------------------------------------------------------
# Data loaders (cached at module level)
# ----------------------------------------------------------------------------

def load_cloud_prices() -> dict:
    return json.loads(CLOUD_PRICES_PATH.read_text())


def load_onprem_assumptions() -> dict:
    return json.loads(ONPREM_PATH.read_text())


def load_perf_benchmarks() -> dict:
    return json.loads(PERF_PATH.read_text())


def cloud_prices_age_days() -> int:
    data = load_cloud_prices()
    return (date.today() - date.fromisoformat(data["as_of"])).days


# ----------------------------------------------------------------------------
# Local tool implementations
#
# Both functions return JSON-serializable dicts; the tool dispatch layer
# stringifies them as the tool_result content.
# ----------------------------------------------------------------------------

def lookup_cloud_price(chip: str, providers: list[str]) -> dict:
    """Read cloud_prices.json and return the cell for each (chip, provider).

    Returns the as_of date and a staleness warning if the snapshot is older
    than 60 days.
    """
    data = load_cloud_prices()
    as_of = data["as_of"]
    age_days = (date.today() - date.fromisoformat(as_of)).days

    pricing = data.get("pricing", {})
    if chip not in pricing:
        return {
            "error": f"Chip '{chip}' not in cloud_prices.json",
            "available_chips": sorted(pricing.keys()),
            "as_of": as_of,
        }

    chip_data = pricing[chip]
    result: dict[str, Any] = {
        "chip": chip,
        "as_of": as_of,
        "snapshot_age_days": age_days,
        "data": {},
    }
    if age_days > STALENESS_THRESHOLD_DAYS:
        result["staleness_warning"] = (
            f"Cloud price snapshot is {age_days} days old (>{STALENESS_THRESHOLD_DAYS}-day threshold). "
            "Verify prices before committing to a contract."
        )
    if "global_notes" in data:
        result["global_notes"] = data["global_notes"]

    available = sorted(chip_data.keys())
    for provider in providers:
        if provider not in chip_data:
            result["data"][provider] = {
                "error": f"Provider '{provider}' not tracked for {chip}",
                "available_providers_for_chip": available,
            }
        else:
            result["data"][provider] = chip_data[provider]

    return result


def _is_liquid_cooled(chip: str) -> bool:
    """Heuristic: Blackwell-class GPUs (B100, B200, GB200) require liquid cooling."""
    upper = chip.upper().replace(" ", "").replace("_", "").replace("-", "")
    return any(token in upper for token in ("B100", "B200", "GB200", "BLACKWELL"))


def compute_tco(
    deployment: str,
    chip: str,
    qty_gpus: int,
    horizon_months: int = 24,
    price_per_gpu_hr: float | None = None,
    capex_usd: float | None = None,
    power_kw_per_gpu: float | None = None,
    utilization_pct: float = 0.7,
    daily_tokens: float | None = None,
) -> dict:
    """Compute capex + opex over a horizon for cloud or on-prem.

    For cloud: pass price_per_gpu_hr (from cloud_prices.json or lookup_cloud_price).
    For on-prem: pass capex_usd and power_kw_per_gpu (typical values: H100/H200
        ~0.7kW, B200 ~1.0kW, MI300X ~0.75kW). On-prem applies electricity at
        $0.10/kWh × PUE × utilization, colocation at $200/kW/month, OEM support
        at 7-8%/yr capex, staff at 10%/yr capex, software at $1500/GPU/yr,
        depreciated over 36 months straight-line per onprem_assumptions.json.

    If daily_tokens is given, also reports amortized $/M tokens.

    Returns a JSON-serializable dict with capex, monthly_opex, opex_horizon,
    and an explicit `assumptions` string.
    """
    onprem = load_onprem_assumptions()
    horizon_hours_total = horizon_months * 730  # 730 ≈ avg hours/month

    result: dict[str, Any] = {
        "deployment": deployment,
        "chip": chip,
        "qty_gpus": qty_gpus,
        "horizon_months": horizon_months,
        "data_source": "Computed locally; on-prem assumptions from onprem_assumptions.json",
    }

    if deployment == "cloud":
        if price_per_gpu_hr is None:
            return {"error": "price_per_gpu_hr is required for deployment='cloud'"}
        monthly_opex = qty_gpus * price_per_gpu_hr * 730
        opex_horizon = qty_gpus * price_per_gpu_hr * horizon_hours_total
        result.update(
            {
                "capex_usd": 0,
                "monthly_opex_usd": round(monthly_opex, 2),
                "opex_horizon_usd": round(opex_horizon, 2),
                "price_per_gpu_hr": price_per_gpu_hr,
                "assumptions": (
                    f"{qty_gpus} GPUs × ${price_per_gpu_hr:.2f}/GPU-hr × 730 hr/mo × {horizon_months} mo. "
                    "Excludes egress, storage, observability, support tooling (typically +5–15%)."
                ),
            }
        )

    elif deployment == "on-prem":
        if capex_usd is None or power_kw_per_gpu is None:
            return {
                "error": "capex_usd and power_kw_per_gpu are required for deployment='on-prem'"
            }

        is_liquid = _is_liquid_cooled(chip)
        pue = onprem["pue"]["liquid_cooled" if is_liquid else "air_cooled"]
        electricity_cost_per_kwh = onprem["electricity"]["default_cost_per_kwh_usd"]
        colo_per_kw_per_month = onprem["colocation"]["monthly_cost_per_kw_usd"]
        cdu_surcharge = onprem["colocation"]["liquid_cooling_cdu_surcharge_monthly_usd"]
        cross_connect = onprem["colocation"]["cross_connects_monthly_usd"]

        # Annual electricity: power × PUE × hours × utilization
        annual_kwh = qty_gpus * power_kw_per_gpu * pue * 8760 * utilization_pct
        annual_electricity = annual_kwh * electricity_cost_per_kwh

        # Annual colocation (rack-level kW for the GPUs and surrounding hardware)
        rack_kw = qty_gpus * power_kw_per_gpu * pue
        annual_colo = rack_kw * colo_per_kw_per_month * 12
        if is_liquid:
            annual_colo += cdu_surcharge * 12
        annual_colo += cross_connect * 12

        # OEM support
        oem_pct = onprem["support_and_staff"]["oem_support_pct_capex_per_year"][
            "blackwell" if is_liquid else "default"
        ]
        annual_oem = capex_usd * oem_pct

        # Staff/SRE allocated to this footprint
        annual_staff = capex_usd * onprem["support_and_staff"]["staff_sre_pct_capex_per_year"]

        # Software
        annual_software = qty_gpus * onprem["support_and_staff"]["software_per_gpu_per_year_usd"]

        annual_opex = annual_electricity + annual_colo + annual_oem + annual_staff + annual_software
        opex_horizon = annual_opex * (horizon_months / 12)

        # Depreciation over the spec's straight-line horizon (default 36mo)
        dep_years = onprem["depreciation"]["horizon_years"]
        dep_horizon_months = dep_years * 12
        depreciated_capex_for_horizon = capex_usd * (
            min(horizon_months, dep_horizon_months) / dep_horizon_months
        )

        tco_horizon_depreciated = depreciated_capex_for_horizon + opex_horizon
        tco_horizon_cash = capex_usd + opex_horizon

        result.update(
            {
                "capex_usd": capex_usd,
                "depreciated_capex_horizon_usd": round(depreciated_capex_for_horizon, 2),
                "annual_opex_breakdown": {
                    "electricity_usd": round(annual_electricity, 2),
                    "colocation_usd": round(annual_colo, 2),
                    "oem_support_usd": round(annual_oem, 2),
                    "staff_sre_usd": round(annual_staff, 2),
                    "software_usd": round(annual_software, 2),
                    "total_usd": round(annual_opex, 2),
                },
                "monthly_opex_usd": round(annual_opex / 12, 2),
                "opex_horizon_usd": round(opex_horizon, 2),
                "tco_horizon_depreciated_usd": round(tco_horizon_depreciated, 2),
                "tco_horizon_cash_usd": round(tco_horizon_cash, 2),
                "pue_used": pue,
                "cooling_assumed": "liquid" if is_liquid else "air",
                "utilization_pct": utilization_pct,
                "assumptions": (
                    f"On-prem assumptions from onprem_assumptions.json (as_of {onprem['as_of']}). "
                    f"Electricity ${electricity_cost_per_kwh}/kWh × PUE {pue} × {qty_gpus}× GPUs × "
                    f"{power_kw_per_gpu}kW/GPU × 8760 hr/yr × {utilization_pct} util. "
                    f"Colo ${colo_per_kw_per_month}/kW/mo. OEM support {oem_pct:.0%}/yr capex. "
                    f"Staff {onprem['support_and_staff']['staff_sre_pct_capex_per_year']:.0%}/yr capex. "
                    f"Depreciation: straight-line over {dep_years}-yr; "
                    f"horizon portion = {min(horizon_months, dep_horizon_months)}/{dep_horizon_months}."
                ),
            }
        )

    else:
        return {"error": f"deployment must be 'cloud' or 'on-prem', got {deployment!r}"}

    if daily_tokens:
        # Approximate: daily × ~30.4 days/month × horizon_months
        total_tokens = daily_tokens * 30.4 * horizon_months
        per_million = result.get("opex_horizon_usd")
        if per_million and total_tokens > 0:
            result["amortized_per_million_tokens_usd"] = round(
                per_million / (total_tokens / 1_000_000), 4
            )

    return result


# ----------------------------------------------------------------------------
# Tool definitions — Anthropic-format tool descriptors
#
# MCP tools are discovered at runtime via list_tools() and adapted via
# `mcp_tools_to_anthropic_tools`. Local tools are hardcoded here.
# ----------------------------------------------------------------------------

LOOKUP_CLOUD_PRICE_TOOL: dict[str, Any] = {
    "name": "lookup_cloud_price",
    "description": (
        "Look up cloud GPU pricing for one chip across one or more providers. "
        "Returns on-demand, 1yr-reserved, and 3yr-reserved $/GPU-hr from the bundled "
        "cloud_prices.json snapshot, including ga_status and last_verified per cell. "
        "Snapshot date is included in the response; warn the user if older than 60 days. "
        "Tracked chips: H100, H200, B200, MI300X. "
        "Tracked providers: AWS, Azure, GCP, Lambda, CoreWeave."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "chip": {
                "type": "string",
                "description": "One of the tracked chips (H100, H200, B200, MI300X).",
            },
            "providers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subset of: AWS, Azure, GCP, Lambda, CoreWeave.",
            },
        },
        "required": ["chip", "providers"],
    },
}


COMPUTE_TCO_TOOL: dict[str, Any] = {
    "name": "compute_tco",
    "description": (
        "Compute total cost of ownership for one deployment configuration over a horizon. "
        "For cloud: pass price_per_gpu_hr (from cloud_prices.json). For on-prem: pass "
        "capex_usd (full server cash price) and power_kw_per_gpu (H100/H200 ~0.7kW, "
        "B200 ~1.0kW, MI300X ~0.75kW). On-prem TCO factors in electricity, PUE, "
        "colocation, OEM support, staff, software, and depreciation per "
        "onprem_assumptions.json. If daily_tokens is provided, also reports "
        "amortized $/M tokens. Returns capex, monthly_opex, opex_horizon, "
        "and an explicit `assumptions` string."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "deployment": {
                "type": "string",
                "enum": ["cloud", "on-prem"],
            },
            "chip": {
                "type": "string",
                "description": "Chip name (e.g., 'H100', 'B200'). Used for cooling heuristic.",
            },
            "qty_gpus": {"type": "integer", "minimum": 1},
            "horizon_months": {"type": "integer", "minimum": 1, "default": 24},
            "price_per_gpu_hr": {
                "type": ["number", "null"],
                "description": "Cloud only: $/GPU-hr from cloud_prices.json.",
            },
            "capex_usd": {
                "type": ["number", "null"],
                "description": "On-prem only: full server cash capex (e.g., ~$300–$500K for 8x H100, ~$500–$800K for 8x B200).",
            },
            "power_kw_per_gpu": {
                "type": ["number", "null"],
                "description": "On-prem only. H100/H200 ~0.7kW; B200 ~1.0kW; MI300X ~0.75kW.",
            },
            "utilization_pct": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "default": 0.7,
                "description": "Sustained utilization fraction (0–1). On-prem requires >0.7 to beat cloud reserved.",
            },
            "daily_tokens": {
                "type": ["number", "null"],
                "description": "Optional. Used to compute amortized $/M tokens.",
            },
        },
        "required": ["deployment", "chip", "qty_gpus"],
    },
}


def respond_with_recommendation_tool() -> dict[str, Any]:
    """Build the final-answer tool descriptor with the TCORecommendation schema.

    The agent must call this tool exactly once at the end with the full ranked
    recommendation. The system prompt (per spec Section E) tells the agent to
    call `respond_with_recommendation(payload=...)`, so the tool's input_schema
    wraps the TCORecommendation model under a `payload` property. The
    validation path (`_unwrap_recommendation_payload`) unwraps tolerantly,
    accepting either shape in case the model drops the wrapper on one turn.
    Pydantic validates client-side; one validation retry is allowed.
    """
    return {
        "name": "respond_with_recommendation",
        "description": (
            "Final answer tool. Call this LAST with the complete TCORecommendation payload "
            "wrapped under the `payload` argument. "
            "Schema is enforced; an invalid payload will be rejected and you will be asked "
            "to retry. The payload includes query_echo (with the user's spec restated and "
            "any interpretations like the SLA reading), recommendation (rank #1), "
            "alternatives (2–3 ranked), rejected_options_summary, risk_flags, "
            "confidence (overall + contributing_tiers), reasoning_summary, and caveats. "
            "Overall confidence MUST equal min(contributing_tiers); high-confidence "
            "recommendations require all contributing tiers to be high."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "payload": TCORecommendation.model_json_schema(),
            },
            "required": ["payload"],
        },
    }


def _unwrap_recommendation_payload(tool_input: Any) -> dict[str, Any]:
    """Return the TCORecommendation-shaped dict from a respond_with_recommendation
    tool input, tolerantly accepting either {"payload": {...}} or {...} directly.

    The system prompt instructs the model to call respond_with_recommendation
    with a `payload` argument (per spec Section E), so the typical shape is
    {"payload": {...TCORecommendation...}}. But under tool_choice forcing or
    after a validation retry the model occasionally drops the wrapper and
    sends fields at the top level. Accept both — TCORecommendation.model_validate
    raises if neither shape is valid.
    """
    if isinstance(tool_input, dict) and "payload" in tool_input and isinstance(
        tool_input["payload"], dict
    ):
        return tool_input["payload"]
    return tool_input if isinstance(tool_input, dict) else {}


LOCAL_TOOL_NAMES = {"lookup_cloud_price", "compute_tco", "respond_with_recommendation"}
LOCAL_TOOL_FUNCTIONS = {
    "lookup_cloud_price": lookup_cloud_price,
    "compute_tco": compute_tco,
}


# ----------------------------------------------------------------------------
# System prompt — verbatim from spec Section E with the 16→10 turn substitution
# ----------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Silicon Analysts Chip TCO Agent. Your job is to take a workload spec
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
6. HONOR HARD CONSTRAINTS. When the user states a numeric constraint (latency
   target, budget cap, timeline, throughput minimum), the #1 recommendation
   MUST satisfy that constraint. If no option in the shortlist can satisfy a
   hard constraint:
   - Surface this prominently in `recommendation.rationale_short` as the
     FIRST sentence: "WARNING: No option in this analysis meets the user's
     stated [X] constraint of [value]. Closest option misses by [delta]."
   - Set `confidence.overall` to 'low' regardless of contributing tier quality.
   - In `caveats`, list which constraint was not met and what would be needed
     (different chip, different commitment, different scale, different
     deployment, or accepting a relaxed constraint).
   - Still produce a ranked output, but the user must clearly see that the
     ranking is "best available" not "constraint-satisfying."

# HARD RULES (DO NOT VIOLATE)

- DO NOT invent prices, throughput numbers, latency numbers, or supply claims.
  Every numerical claim in your output MUST trace to a tool response. If a tool
  returns null/empty for a branch, mark that branch as excluded with a caveat
  and continue with the remaining branches.
- DO NOT label a recommendation `confidence: high` if any contributing input
  was `medium` or `low`. Overall confidence = min(contributing tiers).
- DO NOT exceed 10 reasoning turns. If you reach turn 8, your next action
  MUST be respond_with_recommendation with whatever you have, including
  partial caveats.
- DO NOT recommend an option whose ga_status is "Not offered" or "Not on public
  menu" without explicitly flagging this and why the user might still pursue it
  (e.g., enterprise contract).
- DO NOT silently re-interpret the user's SLA. If you read "p99 <500ms" as
  TTFT-only because end-to-end is infeasible, say so in latency_target_interpreted_as
  AND in caveats.

# HORIZON HANDLING

When the user says a horizon, populate BOTH fields:
  - `horizon_months` — the normalized integer for math (e.g., 30 days → 1,
    24 months → 24, 3 years → 36).
  - `horizon_original` — the verbatim user phrasing (e.g., "30 days",
    "24 months", "3 years"). Used by the renderer for display so users see
    "30 days" instead of "1 months".
If the user did not state a horizon, leave both null and default math to
24 months in your reasoning, noting the assumption in caveats.

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
                horizon_original, budget_cap_usd },
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
"""


# ----------------------------------------------------------------------------
# MCP connection
#
# Streamable HTTP transport with Bearer auth. 10s timeout on initialize +
# list_tools. Friendly diagnostics on common failures.
# ----------------------------------------------------------------------------

class MCPConnectionError(Exception):
    """Wraps any failure during MCP connect/initialize/list_tools with a friendly hint."""


@asynccontextmanager
async def connect_mcp(
    api_key: str,
    url: str = DEFAULT_MCP_URL,
    timeout_s: float = LIST_TOOLS_TIMEOUT_S,
) -> AsyncIterator["ClientSession"]:
    """Connect to the Silicon Analysts MCP server with Bearer auth.

    Yields an initialized ClientSession ready for list_tools() and call_tool().
    Raises MCPConnectionError with a friendly hint on failure.
    """
    from mcp import ClientSession  # lazy import
    from mcp.client.streamable_http import streamablehttp_client  # lazy import

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with streamablehttp_client(url, headers=headers) as (
            read_stream,
            write_stream,
            _get_session_id,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                try:
                    await asyncio.wait_for(session.initialize(), timeout=timeout_s)
                except asyncio.TimeoutError as exc:
                    curl_hint = (
                        f'curl -i -H "Authorization: Bearer $SILICON_ANALYSTS_API_KEY" '
                        f'-H "Content-Type: application/json" '
                        f'-d \'{{"jsonrpc":"2.0","id":1,"method":"initialize","params":{{}}}}\' '
                        f'{url}'
                    )
                    raise MCPConnectionError(
                        f"MCP initialize() timed out after {timeout_s}s against {url}. "
                        f"Reproduce with:\n  {curl_hint}\n"
                        "If you're behind a corporate proxy, set HTTPS_PROXY in your env."
                    ) from exc
                yield session
    except MCPConnectionError:
        raise
    except Exception as exc:  # noqa: BLE001 — top-level diagnostic
        msg = str(exc)
        if "401" in msg or "403" in msg or "Unauthorized" in msg or "Forbidden" in msg:
            raise MCPConnectionError(
                f"MCP auth failed against {url}. Check SILICON_ANALYSTS_API_KEY in your .env. "
                "Get a free key at https://siliconanalysts.com/developers (free tier ≈ 10 queries/day)."
            ) from exc
        if "429" in msg or "Too Many" in msg or "rate" in msg.lower():
            raise MCPConnectionError(
                f"Rate limited by Silicon Analysts MCP (429). The free tier allows 100 API calls/day "
                "(~10 queries). Wait for the daily reset or upgrade at https://siliconanalysts.com/pro."
            ) from exc
        raise MCPConnectionError(
            f"Failed to connect to MCP server at {url}: {type(exc).__name__}: {exc}\n"
            "Check that the URL is reachable from your network and the API key is valid."
        ) from exc


# ----------------------------------------------------------------------------
# Tool adapter — MCP → Anthropic
#
# This is the canonical educational moment of the notebook (per spec Section B).
# Keep it readable. The translation is essentially a field-name change:
# MCP `inputSchema` → Anthropic `input_schema`.
# ----------------------------------------------------------------------------

def mcp_tools_to_anthropic_tools(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """Translate MCP tool definitions to Anthropic tool_use format.

    MCP tool: { name, description, inputSchema (JSON Schema) }
    Anthropic tool: { name, description, input_schema (JSON Schema) }

    The schema content is identical JSON Schema; only the field name differs.
    """
    adapted: list[dict[str, Any]] = []
    for tool in mcp_tools:
        adapted.append(
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema or {"type": "object", "properties": {}},
            }
        )
    return adapted


def build_tools_array(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """Combine MCP tools (adapted) + local tools + final-answer tool."""
    tools = mcp_tools_to_anthropic_tools(mcp_tools)
    tools.append(LOOKUP_CLOUD_PRICE_TOOL)
    tools.append(COMPUTE_TCO_TOOL)
    tools.append(respond_with_recommendation_tool())
    return tools


# ----------------------------------------------------------------------------
# Tool dispatch — runs MCP tools and local tools, returns tool_result blocks
# ----------------------------------------------------------------------------

def _serialize_mcp_result(result: Any) -> str:
    """Convert an MCP CallToolResult into a string suitable for tool_result content."""
    if getattr(result, "isError", False):
        return f"[MCP tool error] {result}"
    pieces: list[str] = []
    for block in getattr(result, "content", []):
        text = getattr(block, "text", None)
        if text is not None:
            pieces.append(text)
        else:
            pieces.append(str(block))
    return "\n".join(pieces) if pieces else "(empty result)"


async def _dispatch_one_tool(
    block: Any,
    mcp_session: "ClientSession",
    console: Console,
    metrics: RunMetrics,
) -> dict[str, Any]:
    """Run one tool_use block; return the corresponding tool_result block."""
    name = block.name
    tool_input = block.input or {}
    started = time.perf_counter()

    try:
        if name in LOCAL_TOOL_FUNCTIONS:
            result_dict = LOCAL_TOOL_FUNCTIONS[name](**tool_input)
            content = json.dumps(result_dict, default=str)
            metrics.local_tool_calls += 1
        elif name == "respond_with_recommendation":
            # Should be handled separately by the caller; if we got here, just acknowledge.
            content = '{"acknowledged": true}'
        else:
            mcp_result = await mcp_session.call_tool(name, tool_input)
            content = _serialize_mcp_result(mcp_result)
            metrics.mcp_tool_calls += 1
        is_error = False
    except Exception as exc:  # noqa: BLE001 — surface failure to the agent
        content = f"Tool {name} failed: {type(exc).__name__}: {exc}"
        is_error = True

    elapsed = time.perf_counter() - started
    color = "red" if is_error else ("yellow" if name in LOCAL_TOOL_NAMES else "cyan")
    console.print(
        f"  [dim]←[/dim] [{color}]{name}[/] [dim]({elapsed * 1000:.0f}ms"
        + (", error" if is_error else "")
        + ")[/dim]"
    )

    block_out: dict[str, Any] = {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": content,
    }
    if is_error:
        block_out["is_error"] = True
    return block_out


async def dispatch_tools(
    tool_use_blocks: list[Any],
    mcp_session: "ClientSession",
    console: Console,
    metrics: RunMetrics,
) -> list[dict[str, Any]]:
    """Dispatch all tool_use blocks in parallel, return tool_result list."""
    return await asyncio.gather(
        *[_dispatch_one_tool(b, mcp_session, console, metrics) for b in tool_use_blocks]
    )


# ----------------------------------------------------------------------------
# Confidence propagation — enforced in code, not just in the prompt
# ----------------------------------------------------------------------------

def enforce_confidence_min(rec: TCORecommendation) -> TCORecommendation:
    """Clamp recommendation.confidence.overall to min(contributing_tiers).

    The spec calls this the "trust contract": if any contributing tier is medium
    or low, the overall cannot be high. The agent is instructed to do this in
    the prompt, but we enforce it here as a safety net. If we override, we add
    a caveat so the user knows.
    """
    contributing = rec.confidence.contributing_tiers
    actual_tiers: list[ConfidenceTier] = []
    for value in contributing.values():
        # Spec entries can be like "high (verified 2026-04-30)" — take the first word.
        first = value.strip().split()[0].lower() if value else ""
        if first in {t.value for t in ConfidenceTier}:
            actual_tiers.append(ConfidenceTier(first))

    if not actual_tiers:
        return rec

    min_tier = min(actual_tiers, key=lambda t: TIER_RANK[t])
    if TIER_RANK[rec.confidence.overall] > TIER_RANK[min_tier]:
        original = rec.confidence.overall.value
        rec.confidence.overall = min_tier
        rec.caveats = list(rec.caveats) + [
            f"[trust contract] Overall confidence was downgraded from "
            f"'{original}' to '{min_tier.value}' to match the lowest contributing tier."
        ]
    return rec


# ----------------------------------------------------------------------------
# Agent loop — single-agent ReAct with streaming, parallel dispatch, retry
# ----------------------------------------------------------------------------

class AgentError(Exception):
    """Raised when the agent loop cannot produce a valid recommendation."""


async def run_agent(
    query: str,
    mcp_session: "ClientSession",
    anthropic_client: "anthropic.AsyncAnthropic",
    *,
    model: str = DEFAULT_MODEL,
    max_turns: int = DEFAULT_MAX_TURNS,
    console: Console | None = None,
) -> tuple[TCORecommendation, RunMetrics]:
    """Run the ReAct loop and return the final structured recommendation.

    The loop:
      1. Lists MCP tools, builds the combined Anthropic tools array.
      2. Streams each turn, printing tool calls as they arrive.
      3. Dispatches tool_use blocks in parallel (asyncio.gather).
      4. Forces respond_with_recommendation via tool_choice when turn >= 8.
      5. Validates the final payload against TCORecommendation; one retry on failure.
      6. Enforces confidence.overall = min(contributing_tiers) post-validation.
    """
    import anthropic  # lazy import (used below in `except anthropic.APIStatusError`)

    console = console or Console()
    metrics = RunMetrics(model=model)
    started = time.perf_counter()

    # 1. Discover MCP tools and build the tools array.
    try:
        mcp_tools_response = await asyncio.wait_for(
            mcp_session.list_tools(), timeout=LIST_TOOLS_TIMEOUT_S
        )
    except asyncio.TimeoutError as exc:
        raise AgentError(f"MCP list_tools() timed out after {LIST_TOOLS_TIMEOUT_S}s.") from exc

    mcp_tools = list(mcp_tools_response.tools)
    tools = build_tools_array(mcp_tools)
    console.print(
        f"[dim]Connected: {len(mcp_tools)} MCP tools "
        f"({', '.join(t.name for t in mcp_tools)}) "
        f"+ 3 local tools.[/dim]"
    )

    messages: list[dict[str, Any]] = [{"role": "user", "content": query}]
    final_payload: dict[str, Any] | None = None
    final_tool_use_id: str | None = None

    for turn in range(max_turns):
        console.rule(f"[bold cyan]Turn {turn + 1}/{max_turns}[/bold cyan]", style="cyan")

        # Force respond_with_recommendation once we hit the trigger turn.
        if turn >= FORCE_RESPOND_AT_TURN:
            tool_choice: dict[str, Any] = {"type": "tool", "name": "respond_with_recommendation"}
            console.print("[dim]→ forcing respond_with_recommendation[/dim]")
        else:
            tool_choice = {"type": "auto"}

        # Stream the response so the user sees text + tool calls in real time.
        text_started = False
        try:
            async with anthropic_client.messages.stream(
                model=model,
                max_tokens=DEFAULT_REQUEST_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=tools,
                tool_choice=tool_choice,
                messages=messages,
            ) as stream:
                async for event in stream:
                    et = getattr(event, "type", None)
                    if et == "content_block_start":
                        block = getattr(event, "content_block", None)
                        if block is not None and getattr(block, "type", None) == "tool_use":
                            console.print(
                                f"  [dim]→[/dim] [bold yellow]{block.name}[/bold yellow]"
                            )
                            text_started = False
                    elif et == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        dt = getattr(delta, "type", None)
                        if dt == "text_delta":
                            text = getattr(delta, "text", "")
                            if not text_started:
                                console.print("  [dim]thinking:[/dim] ", end="")
                                text_started = True
                            console.print(text, end="", soft_wrap=True, highlight=False)
                    elif et == "content_block_stop":
                        if text_started:
                            console.print()
                            text_started = False
                response = await stream.get_final_message()
        except anthropic.APIStatusError as exc:
            raise AgentError(_friendly_anthropic_error(exc)) from exc

        # Track usage.
        metrics.turns += 1
        metrics.input_tokens += response.usage.input_tokens
        metrics.output_tokens += response.usage.output_tokens
        metrics.cache_creation_tokens += getattr(
            response.usage, "cache_creation_input_tokens", 0
        ) or 0
        metrics.cache_read_tokens += getattr(response.usage, "cache_read_input_tokens", 0) or 0

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # Agent emitted only text; nudge it back to tool use.
            messages.append({"role": "assistant", "content": response.content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You must respond by calling the respond_with_recommendation tool. "
                        "Do not return free-form text as the final answer."
                    ),
                }
            )
            continue

        messages.append({"role": "assistant", "content": response.content})

        # Was the final-answer tool called this turn?
        respond_blocks = [b for b in tool_use_blocks if b.name == "respond_with_recommendation"]
        if respond_blocks:
            metrics.tool_calls += 1
            metrics.local_tool_calls += 1
            final_payload = respond_blocks[0].input
            final_tool_use_id = respond_blocks[0].id
            break

        # Otherwise dispatch the tool calls and continue.
        metrics.tool_calls += len(tool_use_blocks)
        tool_results = await dispatch_tools(tool_use_blocks, mcp_session, console, metrics)
        messages.append({"role": "user", "content": tool_results})

    metrics.elapsed_seconds = time.perf_counter() - started

    if final_payload is None:
        raise AgentError(
            f"Agent did not produce a final recommendation after {max_turns} turns."
        )

    # Validate against TCORecommendation; one retry on validation failure.
    # Unwrap the {"payload": {...}} envelope the system prompt asks the agent
    # to use; tolerant of a flat shape if the model dropped the wrapper.
    try:
        result = TCORecommendation.model_validate(
            _unwrap_recommendation_payload(final_payload)
        )
    except ValidationError as exc:
        console.print(f"[yellow]Schema validation failed; retrying once.[/yellow]\n{exc}")
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": final_tool_use_id,
                        "content": (
                            f"Schema validation failed:\n{exc}\n\n"
                            "Please call respond_with_recommendation again with a corrected payload."
                        ),
                        "is_error": True,
                    }
                ],
            }
        )
        retry = await anthropic_client.messages.create(
            model=model,
            max_tokens=DEFAULT_REQUEST_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            tool_choice={"type": "tool", "name": "respond_with_recommendation"},
            messages=messages,
        )
        metrics.input_tokens += retry.usage.input_tokens
        metrics.output_tokens += retry.usage.output_tokens
        metrics.turns += 1
        retry_blocks = [
            b for b in retry.content if b.type == "tool_use" and b.name == "respond_with_recommendation"
        ]
        if not retry_blocks:
            raise AgentError(f"Validation retry produced no respond_with_recommendation call: {exc}")
        result = TCORecommendation.model_validate(
            _unwrap_recommendation_payload(retry_blocks[0].input)
        )

    # Enforce the trust contract.
    result = enforce_confidence_min(result)

    return result, metrics


def _friendly_anthropic_error(exc: anthropic.APIStatusError) -> str:
    code = getattr(exc, "status_code", None)
    if code in (401, 403):
        return (
            f"Anthropic auth failed ({code}). Check ANTHROPIC_API_KEY in your .env. "
            "Get a key at https://console.anthropic.com."
        )
    if code == 429:
        retry_after = getattr(exc, "response", None) and exc.response.headers.get("retry-after")
        return (
            f"Anthropic rate limited (429). "
            + (f"Retry after {retry_after}s. " if retry_after else "")
            + "See https://docs.anthropic.com/claude/reference/rate-limits."
        )
    if code and code >= 500:
        return f"Anthropic server error ({code}): {exc}. Retry in a moment."
    return f"Anthropic API error ({code}): {exc}"


# ----------------------------------------------------------------------------
# Rich rendering
# ----------------------------------------------------------------------------

def _severity_color(severity: str) -> str:
    s = severity.lower()
    if s.startswith("high") or "critical" in s:
        return "red"
    if s.startswith("medium"):
        return "yellow"
    if s.startswith("low"):
        return "blue"
    return "dim"


def _confidence_color(tier: ConfidenceTier | str) -> str:
    val = tier.value if isinstance(tier, ConfidenceTier) else str(tier).lower()
    return {"high": "green", "medium": "yellow", "low": "red"}.get(val, "white")


def render_recommendation(
    rec: TCORecommendation,
    metrics: RunMetrics,
    console: Console | None = None,
) -> None:
    """Render a TCORecommendation + RunMetrics to the terminal using Rich."""
    console = console or Console()
    qe = rec.query_echo

    console.print()
    console.rule("[bold cyan]TCO Recommendation[/bold cyan]", style="cyan")

    # --- Workload echo ----------------------------------------------------
    workload_lines = [f"[bold]{qe.workload}[/bold]"]
    if qe.throughput_target_tokens_per_day:
        line = f"  Throughput: {qe.throughput_target_tokens_per_day:,} tok/day"
        if qe.throughput_target_peak_tps:
            line += f" (peak ~{qe.throughput_target_peak_tps:,.0f} tok/s)"
        workload_lines.append(line)
    if qe.latency_target_p99_ms:
        latency = f"  Latency p99: {qe.latency_target_p99_ms}ms"
        if qe.latency_target_interpreted_as:
            latency += f"\n    ↳ interpreted as: {qe.latency_target_interpreted_as}"
        workload_lines.append(latency)
    if qe.region:
        workload_lines.append(f"  Region: {qe.region}")
    # Prefer the user's verbatim phrasing (e.g., "30 days", "3 years") over
    # the normalized `{N} months` form, which renders as "1 months" for
    # short-horizon queries and confuses users.
    horizon_display = qe.horizon_original or (
        f"{qe.horizon_months} months" if qe.horizon_months else None
    )
    if horizon_display:
        workload_lines.append(f"  Horizon: {horizon_display}")
    if qe.budget_cap_usd:
        workload_lines.append(f"  Budget cap: ${qe.budget_cap_usd:,.0f}")
    console.print(Panel("\n".join(workload_lines), title="Workload", border_style="cyan"))

    # --- Ranked table -----------------------------------------------------
    # The cost-column header carries the horizon explicitly so "$58,000"
    # never reads as "monthly" or "annual" by accident. The amortized-per-
    # M-tokens column is suppressed for short-horizon (<6 months) queries
    # where it overlaps the absolute cost figure (a 30-day bill IS the
    # per-million figure for those workloads), and for queries with no
    # daily-token target where the metric is meaningless.
    horizon_label = (
        f"{qe.horizon_original} $"
        if qe.horizon_original
        else (f"{qe.horizon_months}-mo $" if qe.horizon_months else "Horizon $")
    )
    short_horizon = qe.horizon_months is not None and qe.horizon_months < 6
    no_throughput = not qe.throughput_target_tokens_per_day
    suppress_per_million = short_horizon or no_throughput
    table = Table(title="Ranked options", title_style="bold", show_lines=False)
    table.add_column("#", justify="right")
    table.add_column("Deploy")
    table.add_column("Chip")
    table.add_column("Provider")
    table.add_column("GPUs", justify="right")
    if not suppress_per_million:
        table.add_column("$/M tok", justify="right")
    table.add_column(horizon_label, justify="right")
    table.add_column("Confidence")

    options: list[Option] = [rec.recommendation] + list(rec.alternatives)
    for opt in options:
        amortized = opt.cost_breakdown.amortized_per_million_tokens_usd
        opex = opt.cost_breakdown.opex_24mo_usd or opt.cost_breakdown.opex_horizon_usd
        tier = opt.confidence_tier or rec.confidence.overall
        color = _confidence_color(tier)
        tier_label = tier.value if isinstance(tier, ConfidenceTier) else str(tier)
        row = [
            str(opt.rank),
            opt.deployment.value,
            opt.chip,
            opt.provider,
            str(opt.qty_gpus),
        ]
        if not suppress_per_million:
            row.append(f"${amortized:.3f}" if amortized else "—")
        row.extend([
            f"${opex:,.0f}" if opex else "—",
            f"[{color}]{tier_label}[/{color}]",
        ])
        table.add_row(*row)
    console.print(table)
    if suppress_per_million:
        reason = (
            "no daily throughput in query"
            if no_throughput
            else f"{qe.horizon_months}-month horizon — absolute cost is the meaningful figure"
        )
        console.print(
            f"[dim]   $/M tok column suppressed: {reason}.[/dim]"
        )

    # --- Top recommendation summary --------------------------------------
    top = rec.recommendation
    summary_lines = [
        f"[bold]{top.chip} × {top.qty_gpus} on {top.provider}[/bold] — {top.sku}",
    ]
    if top.rationale_short:
        summary_lines.append(top.rationale_short)
    if top.cost_breakdown.assumptions:
        summary_lines.append(f"\n[dim]{top.cost_breakdown.assumptions}[/dim]")
    if top.ha_posture:
        summary_lines.append(f"[dim]HA: {top.ha_posture}[/dim]")
    console.print(Panel("\n".join(summary_lines), title="Recommendation #1", border_style="green"))

    # --- Risk flags -------------------------------------------------------
    if rec.risk_flags:
        risk_lines = []
        for rf in rec.risk_flags:
            risk_lines.append(
                f"[{_severity_color(rf.severity)}]●[/] [bold]{rf.type}[/bold] "
                f"({rf.severity}): {rf.description}"
            )
            if rf.source_provenance:
                risk_lines.append(f"   [dim]source: {rf.source_provenance}[/dim]")
        console.print(Panel("\n".join(risk_lines), title="Risk flags", border_style="yellow"))

    # --- Confidence -------------------------------------------------------
    overall_color = _confidence_color(rec.confidence.overall)
    contrib_lines = "\n".join(
        f"  • {k}: {v}" for k, v in rec.confidence.contributing_tiers.items()
    )
    console.print(
        Panel(
            f"[bold {overall_color}]Overall: {rec.confidence.overall.value}[/]\n{contrib_lines}",
            title="Confidence",
            border_style=overall_color,
        )
    )

    # --- Reasoning + caveats ---------------------------------------------
    console.print(Panel(rec.reasoning_summary, title="Reasoning", border_style="dim"))
    if rec.caveats:
        caveats_text = "\n".join(f"  • {c}" for c in rec.caveats)
        console.print(Panel(caveats_text, title="Caveats", border_style="dim"))

    # --- Rejected options summary (compact) ------------------------------
    if rec.rejected_options_summary:
        rejected_lines = []
        for name, info in rec.rejected_options_summary.items():
            cost = f" (~${info.opex_24mo_usd:,.0f})" if info.opex_24mo_usd else ""
            rejected_lines.append(f"  [dim]× {name}{cost}: {info.reason_rejected}[/dim]")
        console.print(
            Panel("\n".join(rejected_lines), title="Rejected options", border_style="dim")
        )

    # --- Footer -----------------------------------------------------------
    cloud_data = load_cloud_prices()
    as_of = cloud_data["as_of"]
    age = (date.today() - date.fromisoformat(as_of)).days
    staleness = (
        f" [yellow](snapshot {age}d old, >{STALENESS_THRESHOLD_DAYS}d threshold)[/yellow]"
        if age > STALENESS_THRESHOLD_DAYS
        else ""
    )
    console.print()
    console.print(
        f"[dim]{metrics.tool_calls} tool calls "
        f"({metrics.mcp_tool_calls} MCP, {metrics.local_tool_calls} local) · "
        f"{metrics.turns} turns · {metrics.elapsed_seconds:.1f}s · "
        f"~${metrics.estimated_cost_usd():.3f} on {metrics.model} "
        f"({metrics.input_tokens:,} in / {metrics.output_tokens:,} out tokens) · "
        f"cloud_prices.json as_of {as_of}{staleness}[/dim]"
    )


# ----------------------------------------------------------------------------
# High-level convenience wrappers (used by CLI, examples, and notebook)
# ----------------------------------------------------------------------------

def _load_env_or_fail(console: Console) -> tuple[str, str, str, str, int]:
    """Load .env, validate required keys, return (anth_key, sa_key, mcp_url, model, max_turns)."""
    load_dotenv()
    anth_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    sa_key = os.environ.get("SILICON_ANALYSTS_API_KEY", "").strip()
    if not anth_key:
        console.print(
            "[red]Missing ANTHROPIC_API_KEY.[/red] Set it in .env or your shell. "
            "Get one at https://console.anthropic.com."
        )
        sys.exit(1)
    if not sa_key:
        console.print(
            "[red]Missing SILICON_ANALYSTS_API_KEY.[/red] Set it in .env or your shell. "
            "Get a free key at https://siliconanalysts.com/developers (free tier ≈ 10 queries/day)."
        )
        sys.exit(1)
    mcp_url = os.environ.get("SILICON_ANALYSTS_MCP_URL", DEFAULT_MCP_URL).strip() or DEFAULT_MCP_URL
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    try:
        max_turns = int(os.environ.get("MAX_AGENT_TURNS", str(DEFAULT_MAX_TURNS)))
    except ValueError:
        max_turns = DEFAULT_MAX_TURNS
    return anth_key, sa_key, mcp_url, model, max_turns


async def run_query(
    query: str,
    *,
    console: Console | None = None,
    render: bool = True,
) -> tuple[TCORecommendation, RunMetrics]:
    """Convenience wrapper: load env, connect MCP, run agent, render output.

    Used by the CLI, the notebook, and each examples/0X_*.py script. Keeps
    the agent logic in one place.
    """
    import anthropic  # lazy import (used below to instantiate AsyncAnthropic)

    console = console or Console()
    anth_key, sa_key, mcp_url, model, max_turns = _load_env_or_fail(console)

    age = cloud_prices_age_days()
    if age > STALENESS_THRESHOLD_DAYS:
        console.print(
            f"[yellow]⚠ cloud_prices.json is {age} days old "
            f"(>{STALENESS_THRESHOLD_DAYS}d threshold). Verify before trusting prices.[/yellow]"
        )

    console.rule("[bold]Query[/bold]")
    console.print(query)
    console.print(f"[dim]model={model} max_turns={max_turns} mcp={mcp_url}[/dim]")

    anthropic_client = anthropic.AsyncAnthropic(api_key=anth_key)
    try:
        async with connect_mcp(sa_key, url=mcp_url) as mcp_session:
            result, metrics = await run_agent(
                query,
                mcp_session,
                anthropic_client,
                model=model,
                max_turns=max_turns,
                console=console,
            )
    except MCPConnectionError as exc:
        console.print(f"[red]MCP connection failed:[/red] {exc}")
        raise
    except AgentError as exc:
        console.print(f"[red]Agent failed:[/red] {exc}")
        raise

    if render:
        render_recommendation(result, metrics, console=console)
    return result, metrics


# ----------------------------------------------------------------------------
# CLI entrypoint
# ----------------------------------------------------------------------------

def cli() -> None:
    """CLI: `chip-tco "<query>"` or `python chip_tco_agent.py "<query>"`.

    With no args, prompts interactively. Friendly diagnostics for the common
    failure modes (missing env var, MCP unreachable, 401/429, schema invalid).
    """
    console = Console()
    console.print(Markdown("# Chip TCO Comparison Agent"))

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip()
    else:
        console.print(
            "[dim]Enter a workload spec (Ctrl-D when done), or pass it as a CLI arg.[/dim]"
        )
        try:
            query = sys.stdin.read().strip()
        except KeyboardInterrupt:
            console.print("\nAborted.")
            sys.exit(130)
        if not query:
            console.print("[red]No query provided.[/red]")
            sys.exit(1)

    try:
        asyncio.run(run_query(query, console=console))
    except (MCPConnectionError, AgentError):
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\nAborted.")
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001 — top-level fallback diagnostic
        console.print(f"[red]Unexpected error:[/red] {type(exc).__name__}: {exc}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    cli()
