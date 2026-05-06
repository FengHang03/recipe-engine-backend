from __future__ import annotations

from typing import Dict, List, Optional

from app.domains.ingredients.contracts.dosing import (
    IngredientDosingInfo,
    IngredientDosingUnit,
)


class IngredientDosingService:
    def build_dosing_info(
        self,
        ingredient_id: str,
        dosing_rows_by_ingredient_id: Dict[str, List[dict]],
    ) -> Optional[IngredientDosingInfo]:
        rows = dosing_rows_by_ingredient_id.get(str(ingredient_id), [])
        if not rows:
            return None

        units: List[IngredientDosingUnit] = []
        default_unit_code: Optional[str] = None

        for row in rows:
            unit = IngredientDosingUnit(
                unit_code=str(row["unit_code"]),
                grams_per_unit=float(row["grams_per_unit"]),
                is_default=bool(row.get("is_default", False)),
                min_step_units=float(row.get("min_step_units", 1.0)),
                allow_fractional=bool(row.get("allow_fractional", True)),
                sort_order=int(row.get("sort_order", 0)),
                notes=row.get("notes"),
            )
            units.append(unit)
            if unit.is_default:
                default_unit_code = unit.unit_code

        if default_unit_code is None and units:
            default_unit_code = units[0].unit_code
            
        return IngredientDosingInfo(
            ingredient_id=str(ingredient_id),
            default_unit_code=default_unit_code,
            units=units,
        )
