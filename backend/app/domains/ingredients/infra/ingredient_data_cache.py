"""
ingredient_data_cache.py

Purpose
-------
This file owns the in-memory preload cache for the ingredients support domain.

It is responsible for loading ingredient-related reference data from storage
at application startup and building fast lookup indexes for repeated reads.

Why this file exists
--------------------
Ingredient base rows, tags, and nutrient values are used repeatedly across:
- preset recipe generation
- beginner diy generation
- nutrient analysis
- cooked/raw profile lookup
- future ingredient-related workflows

Without a shared preload cache, these lookups can easily turn into repeated
database queries or N+1 access patterns.

Main responsibilities
---------------------
1. Load active ingredient base rows
2. Load ingredient tags
3. Load ingredient nutrient rows
4. Build reusable lookup indexes, such as:
   - by_ingredient_id
   - by_fdc_id
   - cooked_by_raw_equivalent_fdc_id
   - tags_by_ingredient_id
   - nutrients_by_ingredient_id
5. Provide lightweight retrieval helpers for repositories

Non-responsibilities
--------------------
This file must NOT contain:
- recipe generation logic
- preset resolution logic
- beginner diy category logic
- pet-specific logic
- nutrient interpretation logic
- frontend display logic

Design notes
------------
- This file is part of a lightweight support domain, not a workflow domain.
- Its job is preload + indexing, not orchestration.
- Internal cache row models may stay lightweight and do not need to be
  shared API/domain contracts unless they cross module boundaries.
- Higher-level domains should consume repositories, not this cache directly,
  unless there is a clear low-level reason.

Usage pattern
-------------
Expected runtime lifecycle:
1. App starts
2. IngredientDataCache.load_from_db(...) is called once
3. Cache is stored as an app-level singleton
4. Repositories read from this cache during normal requests

Change policy
-------------
When editing this file:
- keep changes focused on preload, indexing, or cache retrieval
- do not mix in business logic
- avoid speculative abstractions
- document any new index clearly
"""


from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Iterable, Any, Sequence

import pandas as pd
from sqlalchemy.engine import Engine

from app.db.io import read_sql_df


@dataclass
class IngredientRow:
    """Flat cache row for a single active ingredient, mirroring the DB columns used at runtime."""

    ingredient_id: str
    fdc_id: Optional[str]
    description: Optional[str]
    short_name: Optional[str]
    food_group: Optional[str]
    food_subgroup: Optional[str]
    prep_state: Optional[str]
    raw_equivalent_fdc_id: Optional[str]
    yield_factor: Optional[float]
    energy_kcal_per_100g: Optional[float]
    max_g_per_kg_bw: Optional[float]
    max_pct_kcal: Optional[float]
    is_active: bool = True


@dataclass
class IngredientDataCache:
    """
    Preloaded in-memory cache for ingredient base rows, tags, and nutrients.

    Load once at app startup, then let repositories read from these indexes.
    """

    ingredients_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    tags_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    nutrients_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    nutrient_metadata_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    dosing_units_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    by_ingredient_id: Dict[str, IngredientRow] = field(default_factory=dict)
    by_fdc_id: Dict[str, IngredientRow] = field(default_factory=dict)
    cooked_by_raw_equivalent_fdc_id: Dict[str, IngredientRow] = field(default_factory=dict)
    dosing_units_by_ingredient_id: Dict[str, List[dict]] = field(default_factory=dict)

    tags_by_ingredient_id: Dict[str, List[str]] = field(default_factory=dict)
    nutrients_by_ingredient_id: Dict[str, Dict[int, float]] = field(default_factory=dict)
    nutrient_meta_by_id: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    loaded: bool = False

    @classmethod
    def load_from_db(cls, engine: Engine) -> "IngredientDataCache":
        """Query the DB for all active ingredients, tags, nutrients, and nutrient metadata; build indexes."""
        cache = cls()

        ingredients_query = """
        SELECT
            i.id::text AS ingredient_id,
            i.fdc_id::text AS fdc_id,
            i.description,
            i.short_name,
            i.food_group,
            i.food_subgroup,
            i.prep_state,
            i.raw_equivalent_fdc_id::text AS raw_equivalent_fdc_id,
            i.yield_factor,
            i.energy_kcal_per_100g,
            i.max_g_per_kg_bw,
            i.max_pct_kcal,
            i.is_active,
            i.source,
            i.owner_uid
        FROM ingredients i
        WHERE i.is_active = TRUE
        ORDER BY i.description
        """

        tags_query = """
        SELECT
            it.ingredient_id::text AS ingredient_id,
            it.tag
        FROM ingredient_tags it
        ORDER BY it.ingredient_id, it.tag
        """

        nutrients_query = """
        SELECT
            n.ingredient_id::text AS ingredient_id,
            n.nutrient_id::int AS nutrient_id,
            n.amount_per_100g
        FROM ingredient_nutrients n
        ORDER BY n.ingredient_id, n.nutrient_id
        """

        nutrient_metadata_query = """
        SELECT 
            nutrient_id,
            name,
            unit_name,
            is_key,
            group_name
        FROM nutrients
        ORDER BY 
            CASE group_name
                WHEN 'protein_amino' THEN 1
                WHEN 'fat_fatty_acid' THEN 2
                WHEN 'minerals' THEN 3
                WHEN 'vitamins_other' THEN 4
            END,
            display_order NULLS LAST,
            name
        """

        dosing_units_query = """
        SELECT
            ingredient_id::text AS ingredient_id,
            unit_code,
            grams_per_unit,
            is_default,
            min_step_units,
            allow_fractional,
            sort_order,
            notes
        FROM ingredient_dosing_units
        ORDER BY ingredient_id, sort_order, unit_code
        """

        cache.ingredients_df = read_sql_df(engine, ingredients_query)
        cache.tags_df = read_sql_df(engine, tags_query)
        cache.nutrients_df = read_sql_df(engine, nutrients_query)
        cache.nutrient_metadata_df = read_sql_df(engine, nutrient_metadata_query)
        cache.dosing_units_df = read_sql_df(engine, dosing_units_query)

        cache._build_indexes()
        cache.loaded = True
        return cache


    def _build_indexes(self) -> None:
        """Populate all lookup dicts from the raw DataFrames; called once after load_from_db."""
        self.by_ingredient_id.clear()
        self.by_fdc_id.clear()
        self.cooked_by_raw_equivalent_fdc_id.clear()
        self.tags_by_ingredient_id.clear()
        self.nutrients_by_ingredient_id.clear()
        self.dosing_units_by_ingredient_id.clear()

        if not self.ingredients_df.empty:
            for row in self.ingredients_df.to_dict(orient="records"):
                ingredient = IngredientRow(
                    ingredient_id=str(row["ingredient_id"]),
                    fdc_id=self._to_optional_str(row.get("fdc_id")),
                    description=row.get("description"),
                    short_name=row.get("short_name"),
                    food_group=row.get("food_group"),
                    food_subgroup=row.get("food_subgroup"),
                    prep_state=row.get("prep_state"),
                    raw_equivalent_fdc_id=self._to_optional_str(row.get("raw_equivalent_fdc_id")),
                    yield_factor=self._to_optional_float(row.get("yield_factor")),
                    energy_kcal_per_100g=self._to_optional_float(row.get("energy_kcal_per_100g")),
                    max_g_per_kg_bw=self._to_optional_float(row.get("max_g_per_kg_bw")),
                    max_pct_kcal=self._to_optional_float(row.get("max_pct_kcal")),
                    is_active=bool(row.get("is_active", True)),
                )

                self.by_ingredient_id[ingredient.ingredient_id] = ingredient

                if ingredient.fdc_id:
                    self.by_fdc_id[ingredient.fdc_id] = ingredient

                if (
                    ingredient.raw_equivalent_fdc_id
                    and (ingredient.prep_state or "").lower() == "cooked"
                ):
                    self.cooked_by_raw_equivalent_fdc_id[ingredient.raw_equivalent_fdc_id] = ingredient

        if not self.tags_df.empty:
            for row in self.tags_df.to_dict(orient="records"):
                ingredient_id = str(row["ingredient_id"])
                tag = row.get("tag")
                if not tag:
                    continue
                self.tags_by_ingredient_id.setdefault(ingredient_id, []).append(str(tag))

        if not self.nutrients_df.empty:
            for row in self.nutrients_df.to_dict(orient="records"):
                ingredient_id = str(row["ingredient_id"])
                nutrient_id = int(row["nutrient_id"])
                amount = float(row.get("amount_per_100g") or 0.0)
                self.nutrients_by_ingredient_id.setdefault(ingredient_id, {})[nutrient_id] = amount

        if not self.nutrient_metadata_df.empty:
            for row in self.nutrient_metadata_df.to_dict(orient="records"):
                nutrient_id = str(row["nutrient_id"]).strip()
                self.nutrient_meta_by_id[nutrient_id] = row

        self._build_dosing_indexes()

    def get_ingredient_row_by_id(self, ingredient_id: str) -> Optional[IngredientRow]:
        """Return the cached row for a given internal ingredient UUID, or None."""
        return self.by_ingredient_id.get(str(ingredient_id).strip())

    def get_ingredient_row_by_fdc_id(self, fdc_id: str | int) -> Optional[IngredientRow]:
        """Return the cached row matching an FDC ID, or None."""
        return self.by_fdc_id.get(str(fdc_id).strip())

    def get_cooked_row_by_raw_equivalent_fdc_id(
        self,
        raw_equivalent_fdc_id: str | int,
    ) -> Optional[IngredientRow]:
        """Return the cooked-state row whose raw_equivalent_fdc_id matches, or None."""
        return self.cooked_by_raw_equivalent_fdc_id.get(str(raw_equivalent_fdc_id).strip())

    def get_tags(self, ingredient_id: str) -> List[str]:
        """Return a copy of all tags for the ingredient, or an empty list."""
        return list(self.tags_by_ingredient_id.get(str(ingredient_id).strip(), []))

    def get_nutrients(self, ingredient_id: str) -> Dict[int, float]:
        """Return a copy of {nutrient_id: amount_per_100g} for the ingredient, or an empty dict."""
        return dict(self.nutrients_by_ingredient_id.get(str(ingredient_id).strip(), {}))

    def get_nutrient_metadata_row(self, nutrient_id: str | int) -> Optional[dict]:
        """Return the raw metadata dict for a nutrient ID (name, unit, group, etc.), or None."""
        nutrient_key = str(nutrient_id).strip()
        return self.nutrient_meta_by_id.get(nutrient_key)

    def get_rows_by_ids(self, ingredient_ids: Sequence[str]) -> Dict[str, IngredientRow]:
        """Bulk fetch; returns a dict keyed by ingredient_id, silently skipping missing IDs."""
        result: Dict[str, IngredientRow] = {}
        for ingredient_id in ingredient_ids:
            row = self.get_ingredient_row_by_id(ingredient_id)
            if row is not None:
                result[row.ingredient_id] = row
        return result

    def get_rows_by_fdc_ids(self, fdc_ids: Sequence[str | int]) -> Dict[str, IngredientRow]:
        """Bulk fetch by FDC IDs; returns a dict keyed by fdc_id, silently skipping missing IDs."""
        result: Dict[str, IngredientRow] = {}
        for fdc_id in fdc_ids:
            row = self.get_ingredient_row_by_fdc_id(fdc_id)
            if row is not None and row.fdc_id:
                result[str(row.fdc_id)] = row
        return result

    def get_dosing_rows(self, ingredient_id: str) -> List[dict]:
        return list(self.dosing_units_by_ingredient_id.get(str(ingredient_id), []))

    def clear(self) -> None:
        """Reset all DataFrames and indexes to empty; marks the cache as unloaded."""
        self.ingredients_df = pd.DataFrame()
        self.tags_df = pd.DataFrame()
        self.nutrients_df = pd.DataFrame()
        self.nutrient_metadata_df = pd.DataFrame()

        self.by_ingredient_id.clear()
        self.by_fdc_id.clear()
        self.cooked_by_raw_equivalent_fdc_id.clear()
        self.tags_by_ingredient_id.clear()
        self.nutrients_by_ingredient_id.clear()
        self.nutrient_meta_by_id.clear()
        self.loaded = False

    def _to_optional_float(self, value: Any) -> Optional[float]:
        """Coerce value to float, returning None for null or non-numeric input."""
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    def _to_optional_str(self, value: Any) -> Optional[str]:
        """Coerce value to a stripped string, returning None for null or blank input."""
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    def _build_dosing_indexes(self) -> None:
        if self.dosing_units_df is None or self.dosing_units_df.empty:
            self.dosing_units_by_ingredient_id = {}
            return

        working = self.dosing_units_df.copy()
        working["ingredient_id"] = working["ingredient_id"].astype(str)

        grouped = working.groupby("ingredient_id", dropna=False)
        result: Dict[str, List[dict]] = {}

        for ingredient_id, group in grouped:
            records = group.sort_values(
                by=["sort_order", "unit_code"],
                kind="stable",
            ).to_dict(orient="records")
            result[str(ingredient_id)] = records

        self.dosing_units_by_ingredient_id = result
        
