"""
Example: Llama 3.1 7B inference, 10ms TTFT target, EU region, low concurrency
edge deployment.

Exercises latency-dominated reasoning: per-stream tok/s matters more than
aggregate. Agent should filter for EU availability and likely recommend a
smaller GPU footprint (e.g., a single H100 or L40S equivalent) rather than
HGX-class hardware.

Note: cloud_prices.json is US-centric in this snapshot; the agent should
flag EU coverage gaps as a caveat.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chip_tco_agent import run_query  # noqa: E402

QUERY = (
    "Llama 3.1 7B inference, 10ms TTFT target, EU region, "
    "low concurrency edge deployment"
)


def main() -> None:
    asyncio.run(run_query(QUERY))


if __name__ == "__main__":
    main()
