from __future__ import annotations
"""
contracts.py

Stable contracts for the nutrient_analysis domain.

Design goals
------------
- Keep nutrient analysis independent from recipe_generation-specific models
- Accept ingredient amounts + nutrient dataframes as primary inputs
- Keep unit and basis as separate concepts
- Support reusable nutrient contract comparison
"""

from typing import Any, Dict, List, Mapping, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field, ConfigDict

from app.shared.contracts.enums import NutrientID
from app.shared.contracts.ingredient import IngredientProfile
from app.domains.recipe_generation.contracts.constraints import NutrientConstraint
from app.shared.contracts.nutrition import NutrientAnalysis


class AnalysisIngredientItem(BaseModel):
    """
    Minimal ingredient amount input for nutrient analysis.
    """
    ingredient_id: str
    weight_g: float = Field(ge=0)


class NutrientAnalysisInput(BaseModel):
    """
    Unified input contract for nutrient analysis.

    Required dataframes
    -------------------
    ingredient_nutrients_df:
        Long-form dataframe with at least:
        - ingredient_id
        - nutrient_id
        - amount_per_100g

    nutrient_metadata_df:
        Nutrient metadata dataframe with at least:
        - nutrient_id
        - name
        - unit_name

    Notes
    -----
    - ingredient_nutrients_df values are interpreted as "per 100g"
    - unit_name is interpreted as the numerator unit only, e.g. g / mg / ug / iu
    - basis is handled separately in nutrient contracts and analysis logic
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[AnalysisIngredientItem]
    ingredient_nutrients_df: pd.DataFrame
    nutrient_metadata_df: pd.DataFrame
    nutrient_constraints: dict[NutrientID, NutrientConstraint] | None = None
    target_energy_kcal: Optional[float] = Field(default=None, ge=0)
    default_output_basis: str = "per_recipe"


class NutrientAnalysisResult(BaseModel):
    """
    Standard output contract for nutrient analysis.
    """
    # Absolute per-recipe totals in source/raw nutrient unit
    totals_raw_value: Dict[str, Optional[float]] = Field(default_factory=dict)

    # Final display/comparison totals after basis normalization + unit conversion
    totals_display_value: Dict[str, Optional[float]] = Field(default_factory=dict)

    # Source/raw numerator unit from nutrient metadata
    raw_unit_by_nutrient: Dict[str, str] = Field(default_factory=dict)

    # Final numerator unit used for comparison / display
    display_unit_by_nutrient: Dict[str, str] = Field(default_factory=dict)

    # Final basis used for comparison / display
    display_basis_by_nutrient: Dict[str, str] = Field(default_factory=dict)

    analyses: List[NutrientAnalysis] = Field(default_factory=list)
    used_target_calories_kcal: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    debug_meta: Dict[str, Any] = Field(default_factory=dict)

    # totals: Dict[str, Optional[float]] = Field(default_factory=dict)
    