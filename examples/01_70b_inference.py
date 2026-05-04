"""
Example: Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, US-East,
24-month amortization, no budget cap.

This is the headline query — exercises the full agent loop end-to-end:
~10 MCP tool calls (4× get_accelerator_costs in parallel + market_pulse +
packaging + cloud price lookups + compute_tco), 6–8 reasoning turns,
30–60 seconds wall-clock on Sonnet 4.5.

Expected output: H100 or H200 ranks #1 on a neocloud (CoreWeave is cheapest
in our snapshot); B200 typically appears as a runner-up flagged for
benchmark uncertainty.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chip_tco_agent import run_query  # noqa: E402

QUERY = (
    "Llama 3.1 70B inference, 100M tokens/day, p99 <500ms, "
    "US-East, 24-month amortization, no budget cap"
)


def main() -> None:
    asyncio.run(run_query(QUERY))


if __name__ == "__main__":
    main()
