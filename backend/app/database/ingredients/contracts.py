from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, Field


class ThresholdValue(BaseModel):
    value: float
    unit: str

    def __str__(self) -> str:
        return f"{self.value} {self.unit}"

    def __float__(self) -> float:
        return self.value


class TagRule(BaseModel):
    threshold: ThresholdValue
    tag_name: str

    min_raw_value: float = 0.0
    allowed_categories: Optional[List[int]] = None
    excluded_categories: Optional[List[int]] = None
    name_regex: Optional[str] = None

    source_type: str = "DIRECT"
    requires_ca_p_balance: bool = False


class IngredientTagRecord(BaseModel):
    ingredient_id: str
    tags: List[str] = Field(default_factory=list)


@dataclass
class CategoryLimit:
    max_g_per_kg_bw: float | None = None
    max_pct_kcal: float | None = None
    