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
    embodied: bool = True      # spec v0.3 §A.3 embodied channels
    adjacent: bool = True      # spec v0.3 §A.3.5 adjacent and hardware-production employment
    output_substitution: bool = True   # spec v0.3 §A.4
    traded_services: bool = True       # spec v0.3 §A.5.3
