"""
Example: Llama 3.1 8B fine-tune over 1B tokens, budget $50K, 30-day timeline.

Exercises budget-constrained reasoning. The agent should size the cluster
to fit within $50K and 30 days, prefer spot/preemptible tiers where the
framework supports it, and report time-to-completion alongside cost.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chip_tco_agent import run_query  # noqa: E402

QUERY = "Llama 3.1 8B fine-tune over 1B tokens, budget $50K, 30-day timeline"


def main() -> None:
    asyncio.run(run_query(QUERY))


if __name__ == "__main__":
    main()
