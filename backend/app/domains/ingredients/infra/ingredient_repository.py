"""
ingredient_repository.py

Purpose
-------
This file provides repository access for ingredient profile hydration and
ingredient metadata lookup.

It is the main adapter between low-level cached ingredient rows and the
shared domain contract `IngredientProfile`.

Why this file exists
--------------------
Higher-level domains such as preset generation, beginner diy, and nutrient
analysis should not need to know:
- database table structure
- cache index structure
- raw row formats
- tag/nutrient join details

This repository hides those storage and mapping details behind stable methods.

Main responsibilities
---------------------
1. Hydrate IngredientProfile by ingredient_id
2. Hydrate IngredientProfile by fdc_id
3. Support batch hydration for repeated lookups
4. Resolve cooked ingredient profile by raw_equivalent_fdc_id
5. Map cached ingredient rows + tags + nutrient data into IngredientProfile
6. Optionally expose broad ingredient lists for ingredient-selection contexts

Non-responsibilities
--------------------
This file must NOT contain:
- preset recipe orchestration
- beginner diy ratio logic
- pet-profile decisions
- nutrient scoring or interpretation
- explain generation
- endpoint response assembly

Design notes
------------
- Repository methods should prefer preloaded cache whenever available.
- This file should act as the stable entry point for ingredient profile lookup.
- Mapping logic should stay close to the repository because this file owns
  the transition from storage shape to shared contract shape.
- Shared concepts such as IngredientProfile, FoodGroup, FoodSubgroup, and
  NutrientID should be reused rather than redefined here.

Performance philosophy
----------------------
This repository exists partly to avoid repeated DB hydration work.
Preferred flow:
- preload once
- read from cache
- batch where possible
- avoid repeated cooked-profile DB lookups

If performance issues appear, improve:
- cache coverage
- batch lookup behavior
- index structure

Do not solve performance by scattering local caches across unrelated services.

Change policy
-------------
When editing this file:
- preserve method responsibilities
- keep changes surgical
- do not push business logic downward into the repository
- if a new method requires pet profile, recipe mode, or workflow context,
  reconsider whether it belongs here
"""


from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Protocol

import pandas as pd
from sqlalchemy.engine import Engine

from app.db.connection import create_db_engine, dispose_engine
from app.shared.contracts.ingredient import IngredientProfile
from app.shared.contracts.enums import FoodGroup, FoodSubgroup
from app.common.enums import NutrientID

from app.domains.ingredients.infra.ingredient_data_cache import (
    IngredientDataCache,
    IngredientRow,
)


class IngredientDataSource(Protocol):
    def get_ingredient_profiles(self, ingredient_ids: List[str]) -> List[IngredientProfile]:
        ...


class IngredientRepository:
    """
    IngredientRepository

    Responsibility:
    1. Read ingredient profiles from in-memory IngredientDataCache
    2. Provide hydrate-by-id / hydrate-by-fdc-id helpers
    3. Provide cooked-profile lookup by raw_equivalent_fdc_id

    Notes:
    - Prefer cache first.
    - Only own/dispose engine if it created the engine itself.
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

        # 保留你原本 L1 broad query 的 DataFrame cache 能力
        self._cache_l1_ingredients: Optional[pd.DataFrame] = None

    def __enter__(self) -> "IngredientRepository":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
        return False

    def close(self) -> None:
        if self._engine_owned:
            dispose_engine(self._engine)

    def clear_cache(self) -> None:
        self._cache_l1_ingredients = None
        if self._data_cache is not None:
            self._data_cache.clear()

    @property
    def data_cache(self) -> Optional[IngredientDataCache]:
        return self._data_cache

    def set_data_cache(self, data_cache: IngredientDataCache) -> None:
        self._data_cache = data_cache

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_ingredients_for_l1(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Load all active built-in ingredients for L1 filtering.
        If cache already has the full ingredients DataFrame, reuse it.
        """
        if not force_refresh and self._cache_l1_ingredients is not None:
            return self._cache_l1_ingredients

        if self._data_cache is not None and self._data_cache.loaded:
            df = self._data_cache.ingredients_df.copy()
            if not df.empty:
                # 如果你只想保留 built_in，可在这里筛 source；
                # 当前 cache query 里已带 is_active=true，但没保 source
                # 如果后面需要更细筛选，可以在 load_from_db 中多带 source 字段到 dataclass
                self._cache_l1_ingredients = df
                return df

        # fallback：如果你仍想保留旧查库逻辑，可继续加回 broad query
        self._cache_l1_ingredients = pd.DataFrame()
        return self._cache_l1_ingredients

    def get_ingredient_profile(self, ingredient_id: str) -> IngredientProfile:
        result = self.get_ingredient_profiles_by_ids([ingredient_id])
        if ingredient_id not in result:
            raise KeyError(f"Ingredient not found: {ingredient_id}")
        return result[ingredient_id]

    def get_ingredient_profiles_by_ids(
        self,
        ingredient_ids: Sequence[str],
    ) -> Dict[str, IngredientProfile]:
        normalized_ids = self._normalize_str_ids(ingredient_ids)
        if not normalized_ids:
            return {}

        if self._data_cache is None or not self._data_cache.loaded:
            raise RuntimeError("IngredientDataCache is not loaded.")

        rows = self._data_cache.get_rows_by_ids(normalized_ids)

        profiles: Dict[str, IngredientProfile] = {}
        for ingredient_id, row in rows.items():
            profiles[ingredient_id] = self._row_to_ingredient_profile(row)

        return profiles

    def get_ingredient_profiles_by_fdc_ids(
        self,
        fdc_ids: Sequence[str | int],
    ) -> Dict[str, IngredientProfile]:
        normalized_fdc_ids = self._normalize_str_ids(fdc_ids)
        if not normalized_fdc_ids:
            return {}

        if self._data_cache is None or not self._data_cache.loaded:
            raise RuntimeError("IngredientDataCache is not loaded.")

        rows = self._data_cache.get_rows_by_fdc_ids(normalized_fdc_ids)

        profiles: Dict[str, IngredientProfile] = {}
        for fdc_id, row in rows.items():
            profiles[fdc_id] = self._row_to_ingredient_profile(row)

        return profiles

    def get_cooked_profile_by_raw_equivalent_fdc_id(
        self,
        raw_equivalent_fdc_id: str | int,
    ) -> Optional[IngredientProfile]:
        if self._data_cache is None or not self._data_cache.loaded:
            raise RuntimeError("IngredientDataCache is not loaded.")

        row = self._data_cache.get_cooked_row_by_raw_equivalent_fdc_id(raw_equivalent_fdc_id)
        if row is None:
            return None

        return self._row_to_ingredient_profile(row)

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _row_to_ingredient_profile(self, row: IngredientRow) -> IngredientProfile:
        assert self._data_cache is not None

        tags = self._data_cache.get_tags(row.ingredient_id)
        # raw_nutrients = self._data_cache.get_nutrients(row.ingredient_id)

        # nutrients_per_100g: Dict[NutrientID, float] = {}
        # for nutrient_id_int, amount in raw_nutrients.items():
        #     try:
        #         nutrients_per_100g[NutrientID(int(nutrient_id_int))] = float(amount)
        #     except Exception:
        #         continue

        food_group = self._safe_enum(FoodGroup, row.food_group)
        food_subgroup = self._safe_enum(FoodSubgroup, row.food_subgroup)

        return IngredientProfile(
            ingredient_id=row.ingredient_id,
            description=row.description,
            fdc_id=row.fdc_id,
            short_name=row.short_name,
            food_group=food_group,
            food_subgroup=food_subgroup,
            prep_state=row.prep_state,
            raw_equivalent_fdc_id=row.raw_equivalent_fdc_id,
            yield_factor=row.yield_factor,
            tags=tags,
            diversity_cluster=None,
            diversity_tags=[],
            max_g_per_kg_bw=row.max_g_per_kg_bw,
            max_pct_kcal=row.max_pct_kcal,
            energy_per_100g=row.energy_kcal_per_100g,
            nutrients_per_100g={},
            is_supplement=food_group == FoodGroup.SUPPLEMENT,
        )

    # ------------------------------------------------------------------
    # Small utilities
    # ------------------------------------------------------------------

    def _normalize_str_ids(self, values: Iterable[str | int]) -> List[str]:
        result: List[str] = []
        for v in values:
            if v is None:
                continue
            s = str(v).strip()
            if s:
                result.append(s)
        return result

    def _safe_enum(self, enum_cls: Any, raw_value: Any) -> Any:
        if raw_value is None:
            return None
        try:
            return enum_cls(raw_value)
        except Exception:
            return None
            