from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import pandas as pd

from app.domains.ingredients.contracts.catalog import (
    IngredientCatalogItem,
    IngredientCatalogResponse,
)
from app.domains.ingredients.services.ingredient_dosing_service import (
    IngredientDosingService,
)
from app.shared.contracts.enums import (
    FoodGroup, FoodSubgroup
)


class IngredientCatalogService:
    """
    Build lightweight ingredient catalog payloads for frontend ingredient selectors.

    Current target:
    - Beginner DIY

    Data source:
    - IngredientDataCache.ingredients_df
    - IngredientDataCache.tags_df
    - IngredientDataCache.dosing_units_by_ingredient_id

    Notes:
    - This service intentionally does NOT use nutrient long tables.
    - It projects cached ingredient data into a frontend-friendly catalog.
    """

    UI_CATEGORY_MAIN_PROTEIN = "main_protein"
    UI_CATEGORY_ORGAN = "organ"
    UI_CATEGORY_CARB = "carb"
    UI_CATEGORY_VEG_FRUIT = "veg_fruit"
    UI_CATEGORY_OIL_FAT = "oil_fat"
    UI_CATEGORY_EXTRAS_FOOD = "extras_food"
    UI_CATEGORY_SUPPLEMENT = "supplement"

    def __init__(
        self,
        dosing_service: Optional[IngredientDosingService] = None,
    ) -> None:
        self._dosing_service = dosing_service or IngredientDosingService()

    def build_beginner_diy_catalog(
        self,
        ingredients_df: pd.DataFrame,
        tags_df: pd.DataFrame,
        dosing_rows_by_ingredient_id: Optional[Dict[str, List[dict]]] = None,
    ) -> IngredientCatalogResponse:
        if ingredients_df is None or ingredients_df.empty:
            return IngredientCatalogResponse(items=[])

        dosing_rows_by_ingredient_id = dosing_rows_by_ingredient_id or {}
        tag_map = self._build_tag_map(tags_df)

        working = ingredients_df.copy()

        if "is_active" in working.columns:
            working = working[working["is_active"] == True].copy()

        items: List[IngredientCatalogItem] = []

        for row in working.to_dict(orient="records"):
            ingredient_id = self._safe_str(row.get("ingredient_id"))
            if not ingredient_id:
                continue

            description = self._safe_str(row.get("description"))
            if not description:
                continue

            short_name = self._optional_str(row.get("short_name"))
            fdc_id = self._optional_str(row.get("fdc_id"))
            food_group = self._optional_str(row.get("food_group"))
            food_subgroup = self._optional_str(row.get("food_subgroup"))
            prep_state = self._optional_str(row.get("prep_state"))
            kcal_per_100g = self._optional_float(row.get("energy_kcal_per_100g"))

            tags = tag_map.get(ingredient_id, [])

            ui_category = self._map_ui_category(
                food_group=food_group,
                food_subgroup=food_subgroup,
                prep_state=prep_state,
                tags=tags,
                description=description,
                short_name=short_name,
            )
            if ui_category is None:
                continue

            # Beginner DIY currently exposes:
            # - raw foods
            # - supplements (which may be as_is)
            if ui_category != self.UI_CATEGORY_SUPPLEMENT and prep_state != "raw":
                continue

            dosing = self._dosing_service.build_dosing_info(
                ingredient_id=ingredient_id,
                dosing_rows_by_ingredient_id=dosing_rows_by_ingredient_id,
            )

            items.append(
                IngredientCatalogItem(
                    ingredient_id=ingredient_id,
                    description=description,
                    short_name=short_name,
                    fdc_id=fdc_id,
                    food_group=food_group,
                    food_subgroup=food_subgroup,
                    default_slot=self._infer_default_slot(
                        ui_category=ui_category,
                        food_group=food_group,
                        food_subgroup=food_subgroup,
                    ),
                    tags=tags,
                    ui_category=ui_category,
                    kcal_per_100g=kcal_per_100g,
                    prep_state=prep_state,
                    dosing=dosing,
                )
            )

        items.sort(
            key=lambda x: (
                self._ui_category_sort_key(x.ui_category),
                (x.short_name or x.description or "").lower(),
            )
        )

        return IngredientCatalogResponse(items=items)

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _enum_value(value) -> str:
        """
        Accepts Enum members, raw strings, pandas values, or None.
        Returns the enum .value when available; otherwise a stripped string.
        """
        if value is None:
            return ""

        enum_value = getattr(value, "value", None)
        if enum_value is not None:
            return str(enum_value).strip()

        return str(value).strip()

    def _is_food_subgroup(
        self,
        food_subgroup: str,
        candidates: set[FoodSubgroup],
    ) -> bool:
        return food_subgroup in {item.value for item in candidates}

    def _map_ui_category(
        self,
        food_group: Optional[FoodGroup | str],
        food_subgroup: Optional[FoodSubgroup | str],
        prep_state: Optional[str],
        tags: Sequence[str],
        description: str,
        short_name: Optional[str],
    ) -> Optional[str]:
        fg = self._enum_value(food_group).upper()
        fsg = self._enum_value(food_subgroup).lower()
        ps = self._enum_value(prep_state).lower()
        text = f"{description} {short_name or ''}".lower()
        tags_lower = {str(t).strip().lower() for t in tags if t and str(t).strip()}

        # ------------------------------------------------------------------
        # 1) food_group: strongest signal
        # ------------------------------------------------------------------

        if fg == FoodGroup.SUPPLEMENT.value:
            return self.UI_CATEGORY_SUPPLEMENT

        # Mineral shellfish is used as a small functional/mineral source,
        # not as a main protein.
        if fg == FoodGroup.MINERAL_SHELLFISH.value:
            return self.UI_CATEGORY_EXTRAS_FOOD

        if fg == FoodGroup.PROTEIN_SHELLFISH.value:
            return self.UI_CATEGORY_EXTRAS_FOOD

        if fg == FoodGroup.FAT_OIL.value:
            return self.UI_CATEGORY_OIL_FAT

        if fg == FoodGroup.ORGAN.value:
            return self.UI_CATEGORY_ORGAN

        if fg in {
            FoodGroup.PROTEIN_MEAT.value,
            FoodGroup.PROTEIN_FISH.value,
            FoodGroup.PROTEIN_EGG.value,
            FoodGroup.PROTEIN_SHELLFISH.value,
            FoodGroup.DAIRY.value,
        }:
            return self.UI_CATEGORY_MAIN_PROTEIN

        if fg in {
            FoodGroup.CARB_GRAIN.value,
            FoodGroup.CARB_TUBER.value,
            FoodGroup.CARB_LEGUME.value,
            FoodGroup.CARB_OTHER.value,
        }:
            return self.UI_CATEGORY_CARB

        if fg in {
            FoodGroup.PLANT_ANTIOXIDANT.value,
            FoodGroup.FIBER.value,
        }:
            return self.UI_CATEGORY_VEG_FRUIT

        # Treats are not exposed in Beginner DIY recipe builder for now.
        if fg == FoodGroup.TREAT.value:
            return None

        # ------------------------------------------------------------------
        # 2) food_subgroup: second strongest signal
        # ------------------------------------------------------------------

        if self._is_food_subgroup(
            fsg,
            {
                FoodSubgroup.SUPPLEMENT_CALCIUM,
                FoodSubgroup.SUPPLEMENT_IODINE,
                FoodSubgroup.SUPPLEMENT_OMEGA3,
                FoodSubgroup.SUPPLEMENT_OTHER,
                FoodSubgroup.FIBER_SUPPLEMENT,
            },
        ):
            return self.UI_CATEGORY_SUPPLEMENT

        if fsg == FoodSubgroup.MINERAL_SHELLFISH.value:
            return self.UI_CATEGORY_EXTRAS_FOOD

        if self._is_food_subgroup(
            fsg,
            {
                FoodSubgroup.OIL_OMEGA3_LC,
                FoodSubgroup.OIL_OMEGA6_LA,
            },
        ):
            return self.UI_CATEGORY_OIL_FAT

        if self._is_food_subgroup(
            fsg,
            {
                FoodSubgroup.LIVER,
                FoodSubgroup.KIDNEY,
                FoodSubgroup.SPLEEN,
                FoodSubgroup.BRAIN,
                FoodSubgroup.ORGAN_SECRETING,
                FoodSubgroup.HEART,
                FoodSubgroup.GIZZARD,
                FoodSubgroup.ORGAN_MUSCULAR,
            },
        ):
            return self.UI_CATEGORY_ORGAN

        if self._is_food_subgroup(
            fsg,
            {
                FoodSubgroup.CARB_GRAIN,
                FoodSubgroup.CARB_TUBER,
                FoodSubgroup.CARB_LEGUME,
            },
        ):
            return self.UI_CATEGORY_CARB

        if self._is_food_subgroup(
            fsg,
            {
                FoodSubgroup.PLANT_ORANGE,
                FoodSubgroup.PLANT_GREEN,
                FoodSubgroup.PLANT_BLUE,
                FoodSubgroup.PLANT_WHITE,
                FoodSubgroup.PLANT_OTHER,
                FoodSubgroup.FIBER_PLANT,
            },
        ):
            return self.UI_CATEGORY_VEG_FRUIT

        if self._is_food_subgroup(
            fsg,
            {
                FoodSubgroup.MEAT_LEAN,
                FoodSubgroup.MEAT_MODERATE,
                FoodSubgroup.MEAT_FAT,
                FoodSubgroup.FISH_LEAN,
                FoodSubgroup.FISH_OILY,
                FoodSubgroup.PROTEIN_SHELLFISH,
                FoodSubgroup.EGG,
                FoodSubgroup.DAIRY,
            },
        ):
            return self.UI_CATEGORY_MAIN_PROTEIN

        # ------------------------------------------------------------------
        # 3) tags: auxiliary signal
        # ------------------------------------------------------------------

        if (
            ps == "as_is"
            and (
                "calcium" in tags_lower
                or "iodine" in tags_lower
                or "supplement" in tags_lower
            )
        ):
            return self.UI_CATEGORY_SUPPLEMENT

        if (
            "supplement" in tags_lower
            or "calcium" in tags_lower
            or "iodine" in tags_lower
            or "vitamin" in tags_lower
            or "mineral" in tags_lower
        ):
            return self.UI_CATEGORY_SUPPLEMENT

        if "organ" in tags_lower or "liver" in tags_lower or "kidney" in tags_lower:
            return self.UI_CATEGORY_ORGAN

        if "fat_oil" in tags_lower or "oil_fat" in tags_lower:
            return self.UI_CATEGORY_OIL_FAT

        if (
            "shellfish" in tags_lower
            or "extra" in tags_lower
            or "mollusk" in tags_lower
            or "bivalve" in tags_lower
        ):
            return self.UI_CATEGORY_EXTRAS_FOOD

        if "carb" in tags_lower or "grain" in tags_lower:
            return self.UI_CATEGORY_CARB

        if "veg" in tags_lower or "fruit" in tags_lower:
            return self.UI_CATEGORY_VEG_FRUIT

        if "protein" in tags_lower:
            return self.UI_CATEGORY_MAIN_PROTEIN

        # ------------------------------------------------------------------
        # 4) text fallback: weakest signal, only if fg/fsg/tags missed
        # ------------------------------------------------------------------

        if (
            "fish oil" in text
            or "salmon oil" in text
            or "sunflower oil" in text
            or "flaxseed oil" in text
            or "olive oil" in text
            or "coconut oil" in text
        ):
            return self.UI_CATEGORY_OIL_FAT

        if (
            "oyster" in text
            or "mussel" in text
            or "clam" in text
        ):
            return self.UI_CATEGORY_EXTRAS_FOOD

        if (
            "liver" in text
            or "kidney" in text
            or "spleen" in text
            or "heart" in text
            or "gizzard" in text
        ):
            return self.UI_CATEGORY_ORGAN

        if (
            "beef" in text
            or "chicken" in text
            or "turkey" in text
            or "duck" in text
            or "pork" in text
            or "lamb" in text
            or "salmon" in text
            or "sardine" in text
            or "egg" in text
        ):
            return self.UI_CATEGORY_MAIN_PROTEIN

        if (
            "rice" in text
            or "oat" in text
            or "sweet potato" in text
            or "potato" in text
            or "quinoa" in text
        ):
            return self.UI_CATEGORY_CARB

        if (
            "berry" in text
            or "carrot" in text
            or "spinach" in text
            or "broccoli" in text
            or "pumpkin" in text
            or "green bean" in text
            or "beans" in text
        ):
            return self.UI_CATEGORY_VEG_FRUIT

        return None

    def _infer_default_slot(
        self,
        ui_category: str,
        food_group: Optional[str],
        food_subgroup: Optional[str],
    ) -> Optional[str]:
        if ui_category == self.UI_CATEGORY_MAIN_PROTEIN:
            return "main_protein"
        if ui_category == self.UI_CATEGORY_ORGAN:
            return "organ"
        if ui_category == self.UI_CATEGORY_CARB:
            return "carb"
        if ui_category == self.UI_CATEGORY_VEG_FRUIT:
            return "veg_fruit"
        if ui_category == self.UI_CATEGORY_OIL_FAT:
            return "oil_fat"
        if ui_category == self.UI_CATEGORY_EXTRAS_FOOD:
            return "extras_food"
        if ui_category == self.UI_CATEGORY_SUPPLEMENT:
            return "supplement"
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_tag_map(self, tags_df: pd.DataFrame) -> Dict[str, List[str]]:
        if tags_df is None or tags_df.empty:
            return {}

        working = tags_df.copy()
        working["ingredient_id"] = working["ingredient_id"].astype(str)
        working["tag"] = working["tag"].astype(str)

        grouped = (
            working.groupby("ingredient_id", dropna=False)["tag"]
            .apply(list)
            .to_dict()
        )

        result: Dict[str, List[str]] = {}
        for ingredient_id, raw_tags in grouped.items():
            clean_tags = sorted(
                {
                    str(tag).strip()
                    for tag in raw_tags
                    if tag is not None and str(tag).strip()
                }
            )
            result[str(ingredient_id)] = clean_tags

        return result

    def _ui_category_sort_key(self, ui_category: str) -> int:
        order = {
            self.UI_CATEGORY_MAIN_PROTEIN: 1,
            self.UI_CATEGORY_ORGAN: 2,
            self.UI_CATEGORY_CARB: 3,
            self.UI_CATEGORY_VEG_FRUIT: 4,
            self.UI_CATEGORY_OIL_FAT: 5,
            self.UI_CATEGORY_EXTRAS_FOOD: 6,
            self.UI_CATEGORY_SUPPLEMENT: 7,
        }
        return order.get(ui_category, 999)

    def _safe_str(self, value) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _optional_str(self, value) -> Optional[str]:
        text = self._safe_str(value)
        return text or None

    def _optional_float(self, value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None
