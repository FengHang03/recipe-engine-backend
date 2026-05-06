from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field
from app.domains.ingredients.contracts.dosing import IngredientDosingInfo


class IngredientCatalogItem(BaseModel):
    ingredient_id: str
    description: str
    short_name: Optional[str] = None
    fdc_id: Optional[str] = None
    food_group: Optional[str] = None
    food_subgroup: Optional[str] = None
    default_slot: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    ui_category: str
    kcal_per_100g: Optional[float] = None
    prep_state: Optional[str] = None
    dosing: Optional[IngredientDosingInfo] = None


class IngredientCatalogResponse(BaseModel):
    items: List[IngredientCatalogItem] = Field(default_factory=list)
