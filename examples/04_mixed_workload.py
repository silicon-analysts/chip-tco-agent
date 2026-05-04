"""
Example: Mixed workload — 50% Llama 70B inference, 50% Stable Diffusion XL
image generation, 24-month horizon.

Exercises decomposition: the two sub-workloads have different memory and
compute profiles. Agent should either size a single shared cluster or
recommend a heterogeneous fleet (e.g., H200 for the LLM half, L40S/H100
for SDXL) with a combined TCO and an explicit operational tradeoff.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chip_tco_agent import run_query  # noqa: E402

QUERY = (
    "Mixed workload: 50% Llama 70B inference, 50% Stable Diffusion XL "
    "image gen, 24-month horizon"
)


def main() -> None:
    asyncio.run(run_query(QUERY))


if __name__ == "__main__":
    main()
