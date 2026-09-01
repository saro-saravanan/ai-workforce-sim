"""Channel switches for the decomposition (spec §9). The labor equations live in mc.py."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Channels:
    automation: bool = True
    augmentation: bool = True
    demand_response: bool = True
    reinstatement: bool = True
    demand_feedback: bool = True
    ai_investment: bool = True
