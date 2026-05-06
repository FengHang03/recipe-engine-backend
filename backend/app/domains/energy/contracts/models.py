from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel


class EnergyCalculationResult(BaseModel):
    resting_energy_kcal: float
    daily_energy_kcal: float
    target_kcal_range: Tuple[float, float]
    life_stage: str
    model_version: str
    calculation_breakdown: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    confidence: str = "high"
    adult_energy_profiles: Optional[Dict[str, float]] = None
    default_adult_profile: Optional[str] = None