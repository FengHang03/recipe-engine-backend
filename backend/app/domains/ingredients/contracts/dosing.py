from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

class IngredientDosingUnit(BaseModel):
    unit_code: str
    grams_per_unit: float
    is_default: bool = False
    min_step_units: float = 1.0
    allow_fractional: bool = True
    sort_order: int = 0
    notes: Optional[str] = None


class IngredientDosingInfo(BaseModel):
    default_unit_code: Optional[str] = None
    units: List[IngredientDosingUnit] = Field(default_factory=list)
