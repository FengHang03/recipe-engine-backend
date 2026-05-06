from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .classifiers import get_category_hint_from_id, get_diversity_tag, infer_food_category
from .cleaners import get_short_name
from .nutrient_ids import NutrientID, NutrientMeta
from .target_config import TargetConfig

logger = logging.getLogger(__name__)


def build_nutrients_table(input_file_path: str, output_file_path: str | None = None) -> pd.DataFrame:
    df = pd.read_csv(input_file_path).copy()

    if "nutrient_id" not in df.columns:
        raise ValueError("nutrient csv must contain 'nutrient_id'")

    df["nutrient_id"] = pd.to_numeric(df["nutrient_id"], errors="coerce").fillna(0).astype(int)
    df = df[df["nutrient_id"].isin(TargetConfig.get_all_nut_id())].copy()

    keep_cols = [c for c in ["nutrient_id", "name", "unit_name"] if c in df.columns]
    result = df[keep_cols].drop_duplicates(subset=["nutrient_id"]).copy()
    result = result.rename(columns={"nutrient_id": "id", "unit_name": "unit"})

    if "name" not in result.columns:
        result["name"] = result["id"].apply(NutrientMeta.get_name)

    if "unit" not in result.columns:
        result["unit"] = result["id"].apply(NutrientMeta.get_unit)

    result = result.sort_values("id").reset_index(drop=True)

    if output_file_path:
        Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_file_path, index=False)

    return result


def build_ingredients_table(
    input_file_path: str,
    output_file_path: str | None = None,
    merge_strategy: str = "replace",
) -> pd.DataFrame:

    column_order = [
        "id",
        "source",
        "owner_uid",
        "fdc_id",
        "description",
        "short_name",
        "food_category_id",
        "food_category_label",
        "food_group",
        "energy_kcal_per_100g",
        "prep_state",
        "yield_factor",
        "raw_equivalent_fdc_id",
        "is_active",
        "max_g_per_kg_bw",
        "max_pct_kcal",
        "created_at",
        "updated_at",
    ]
    df = pd.read_csv(input_file_path).copy()

    if "fdc_id" not in df.columns:
        raise ValueError("food csv must contain 'fdc_id'")
    if "description" not in df.columns:
        raise ValueError("food csv must contain 'description'")

    target_fdc_ids = set(TargetConfig.get_all_fdc_id())
    df["fdc_id"] = pd.to_numeric(df["fdc_id"], errors="coerce").fillna(0).astype(int)
    df = df[df["fdc_id"].isin(target_fdc_ids)].copy()

    now_str = datetime.now(timezone.utc).isoformat()

    df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]
    df["short_name"] = df["description"].apply(get_short_name)
    df["food_group"] = df["description"].apply(infer_food_category)

    if "food_category_id" in df.columns:
        fat_col = "fat" if "fat" in df.columns else None
        df["category_hint"] = df.apply(
            lambda row: get_category_hint_from_id(
                category_id=int(row["food_category_id"]) if pd.notna(row["food_category_id"]) else -1,
                description=str(row["description"]),
                fat_g_100g=float(row[fat_col]) if fat_col and pd.notna(row[fat_col]) else None,
            ),
            axis=1,
        )
        df["diversity_tag"] = df.apply(get_diversity_tag, axis=1)
    else:
        df["category_hint"] = None
        df["diversity_tag"] = None

    if "food_category_id" in df.columns:
        df["food_subgroup"] = df["category_hint"]
    else:
        df["food_subgroup"] = None

    df["max_g_per_kg_bw"] = None
    df["max_pct_kcal"] = None
    df["is_active"] = True
    df["created_at"] = now_str
    df["updated_at"] = now_str

    keep_cols = [
        "id",
        "fdc_id",
        "description",
        "short_name",
        "food_category_id",
        "inferred_category",
        "category_hint",
        "food_subgroup",
        "diversity_tag",
        "max_g_per_kg_bw",
        "max_pct_kcal",
        "is_active",
        "created_at",
        "updated_at",
    ]
    keep_cols = [c for c in keep_cols if c in df.columns]

    result = df[keep_cols].drop_duplicates(subset=["fdc_id"]).reset_index(drop=True)

    if output_file_path:
        Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_file_path, index=False)

    return result


def build_ingredient_nutrients_table(
    input_food_path: str,
    input_nut_path: str,
    output_file_path: str | None = None,
) -> pd.DataFrame:
    ordered_target_nut_ids = TargetConfig.get_all_nut_id()
    target_nut_ids = set(ordered_target_nut_ids)

    food_df = pd.read_csv(input_food_path, usecols=["id", "fdc_id"]).copy()
    food_df["fdc_id"] = pd.to_numeric(food_df["fdc_id"], errors="coerce").fillna(0).astype(int)
    food_df = food_df.rename(columns={"id": "ingredient_id"})

    nut_df = pd.read_csv(input_nut_path).copy()
    nut_df["fdc_id"] = pd.to_numeric(nut_df["fdc_id"], errors="coerce").fillna(0).astype(int)
    nut_df["nutrient_id"] = pd.to_numeric(nut_df["nutrient_id"], errors="coerce").fillna(0).astype(int)

    if "amount" not in nut_df.columns:
        raise ValueError("food_nutrient csv must contain 'amount'")

    nut_df = nut_df[nut_df["nutrient_id"].isin(target_nut_ids)].copy()

    merged = nut_df.merge(food_df, on="fdc_id", how="inner")
    merged = merged.rename(columns={"amount": "amount_per_100g"})
    merged["amount_per_100g"] = pd.to_numeric(merged["amount_per_100g"], errors="coerce").fillna(0.0)

    keep_cols = ["ingredient_id", "nutrient_id", "amount_per_100g"]
    result = merged[keep_cols].drop_duplicates(subset=["ingredient_id", "nutrient_id"]).copy()

    rank_lookup = {nid: i for i, nid in enumerate(ordered_target_nut_ids)}
    result["__rank"] = result["nutrient_id"].map(lambda x: rank_lookup.get(int(x), 999999))
    result = result.sort_values(["ingredient_id", "__rank"]).drop(columns="__rank").reset_index(drop=True)

    if output_file_path:
        Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_file_path, index=False)

    return result
    
def build_energy_map(food_nutrient_csv: str) -> dict[int, float]:
    df = pd.read_csv(food_nutrient_csv, usecols=["fdc_id", "nutrient_id", "amount"]).copy()
    df["fdc_id"] = pd.to_numeric(df["fdc_id"], errors="coerce").fillna(0).astype(int)
    df["nutrient_id"] = pd.to_numeric(df["nutrient_id"], errors="coerce").fillna(0).astype(int)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    df = df[df["nutrient_id"] == NutrientID.ENERGY].copy()
    df = df.groupby("fdc_id", as_index=False)["amount"].first()

    return dict(zip(df["fdc_id"], df["amount"]))