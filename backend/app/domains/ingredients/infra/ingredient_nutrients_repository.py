"""
ingredient_nutrients_repository.py

Purpose
-------
This file provides repository access for ingredient nutrient values and
nutrient matrix generation.

It is the nutrient-focused companion to ingredient_repository.py.

Why this file exists
--------------------
Multiple higher-level domains need ingredient nutrient data in reusable forms:
- nutrient analysis
- L2 optimization
- diagnostics
- future debugging / reporting tools

This repository centralizes nutrient lookup so those domains do not need to
query storage or understand cache internals directly.

Main responsibilities
---------------------
1. Get nutrient values for a single ingredient
2. Get nutrient values for multiple ingredients
3. Return long-form nutrient rows when needed
4. Build wide nutrient matrices for downstream analysis / optimization
5. Read nutrient data from the shared ingredient preload cache

Non-responsibilities
--------------------
This file must NOT contain:
- nutrient interpretation
- AAFCO rule evaluation
- L2 solving logic
- recipe generation orchestration
- preset-specific logic
- beginner diy category rules
- frontend display logic

Design notes
------------
- This repository should focus on data access shape, not business meaning.
- It should expose nutrient data in forms that downstream consumers can use
  directly, such as:
  - dict mappings
  - long DataFrames
  - wide matrices
- Interpretation of whether nutrient values are adequate, excessive, or risky
  belongs in higher-level analysis or rule-engine modules.

Performance philosophy
----------------------
Nutrient lookup is often repeated and should rely on preloaded in-memory data
when possible.

Preferred pattern:
- cache nutrient rows once
- expose lightweight lookup helpers
- build analysis/optimization matrices from cache
- avoid repeated database scans during request handling

Change policy
-------------
When editing this file:
- keep concerns limited to nutrient retrieval and matrix shaping
- avoid mixing nutrient business rules into repository code
- prefer reusable return shapes over one-off special cases
"""


from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd
from sqlalchemy.engine import Engine

from app.db.connection import create_db_engine, dispose_engine
from app.domains.ingredients.infra.ingredient_data_cache import IngredientDataCache


class IngredientNutrientsRepository:
    """
    Repository for ingredient nutrient lookups and L2 nutrition matrix building.

    Reads from preloaded IngredientDataCache.
    """

    def __init__(
        self,
        engine: Optional[Engine] = None,
        connection_string: Optional[str] = None,
        data_cache: Optional[IngredientDataCache] = None,
    ) -> None:
        if engine is not None:
            self._engine = engine
            self._engine_owned = False
        else:
            self._engine = create_db_engine(connection_string)
            self._engine_owned = True

        self._data_cache = data_cache

    def __enter__(self) -> "IngredientNutrientsRepository":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
        return False

    def close(self) -> None:
        if self._engine_owned:
            dispose_engine(self._engine)

    def set_data_cache(self, data_cache: IngredientDataCache) -> None:
        self._data_cache = data_cache

    def get_nutrients_by_ingredient_id(
        self,
        ingredient_id: str,
    ) -> Dict[int, float]:
        if self._data_cache is None or not self._data_cache.loaded:
            raise RuntimeError("IngredientDataCache is not loaded.")
        return self._data_cache.get_nutrients(ingredient_id)

    def get_nutrients_by_ingredient_ids(
        self,
        ingredient_ids: Sequence[str],
    ) -> Dict[str, Dict[int, float]]:
        if self._data_cache is None or not self._data_cache.loaded:
            raise RuntimeError("IngredientDataCache is not loaded.")

        result: Dict[str, Dict[int, float]] = {}
        for ingredient_id in ingredient_ids:
            ingredient_id = str(ingredient_id).strip()
            if not ingredient_id:
                continue
            result[ingredient_id] = self._data_cache.get_nutrients(ingredient_id)
        return result

    def get_nutrient_metadata_df(
        self,
        nutrient_ids: Optional[Sequence[str | int]] = None,
    ) -> pd.DataFrame:
        if self._data_cache is None or not self._data_cache.loaded:
            raise RuntimeError("Nutrient metadata cache is not loaded.")

        df = self._data_cache.nutrient_metadata_df
        if nutrient_ids is None:
            return df.copy()

        normalized_ids = set()
        for v in nutrient_ids:
            if v is None:
                continue
            try:
                normalized_ids.add(int(v))
            except Exception:
                continue

        if not normalized_ids:
            return pd.DataFrame(
                columns=["nutrient_id", "name", "unit_name", "is_key", "group_name"]
            )

        return df[df["nutrient_id"].isin(normalized_ids)].copy()

    def get_nutrition_long_df(
        self,
        ingredient_ids: Optional[Sequence[str]] = None,
    ) -> pd.DataFrame:
        if self._data_cache is None or not self._data_cache.loaded:
            raise RuntimeError("IngredientDataCache is not loaded.")

        df = self._data_cache.nutrients_df
        if ingredient_ids is None:
            return df.copy()

        normalized_ids = {str(v).strip() for v in ingredient_ids if str(v).strip()}
        if not normalized_ids:
            return pd.DataFrame(columns=["ingredient_id", "nutrient_id", "amount_per_100g"])

        return df[df["ingredient_id"].isin(normalized_ids)].copy()

    def get_nutrition_matrix_for_l2(
        self,
        ingredient_ids: Sequence[str],
    ) -> pd.DataFrame:
        """
        Return wide matrix:
            index   = ingredient_id
            columns = nutrient_id
            values  = amount_per_100g
        """
        long_df = self.get_nutrition_long_df(ingredient_ids)
        if long_df.empty:
            return pd.DataFrame(index=list(ingredient_ids))

        wide_df = long_df.pivot(
            index="ingredient_id",
            columns="nutrient_id",
            values="amount_per_100g",
        ).fillna(0.0)

        for ingredient_id in ingredient_ids:
            ingredient_id = str(ingredient_id).strip()
            if ingredient_id and ingredient_id not in wide_df.index:
                wide_df.loc[ingredient_id] = 0.0

        wide_df = wide_df.sort_index()
        return wide_df