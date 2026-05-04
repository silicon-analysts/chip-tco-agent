"""
Example: On-prem vs cloud comparison for Llama 70B inference at 200M tokens/day,
36-month horizon.

Exercises the full on-prem TCO path: capex + electricity + PUE + colo +
OEM support + staff + software + 36mo straight-line depreciation. At 200M
tokens/day and 36 months, the on-prem case strengthens vs the spec's
24-month worked example — the agent should show the crossover utilization
threshold explicitly (>70% per onprem_assumptions.json).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chip_tco_agent import run_query  # noqa: E402

QUERY = (
    "On-prem vs cloud comparison for Llama 70B inference at 200M tokens/day, "
    "36-month horizon"
)


def main() -> None:
    asyncio.run(run_query(QUERY))


if __name__ == "__main__":
    main()
