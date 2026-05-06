from fastapi import APIRouter, Depends, Request

from app.domains.ingredients.contracts.catalog import IngredientCatalogResponse
from app.domains.ingredients.services.ingredient_catalog_service import IngredientCatalogService

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


def get_ingredient_catalog_service() -> IngredientCatalogService:
    return IngredientCatalogService()


@router.get("/catalog", response_model=IngredientCatalogResponse)
async def get_ingredient_catalog(
    request: Request,
    mode: str = "beginner_diy",
    service: IngredientCatalogService = Depends(get_ingredient_catalog_service),
) -> IngredientCatalogResponse:
    if mode != "beginner_diy":
        return IngredientCatalogResponse(items=[])

    data_cache = getattr(request.app.state, "ingredient_data_cache", None)
    if data_cache is None or not getattr(data_cache, "loaded", False):
        return IngredientCatalogResponse(items=[])

    return service.build_beginner_diy_catalog(
        ingredients_df=data_cache.ingredients_df,
        tags_df=data_cache.tags_df,
        dosing_rows_by_ingredient_id=data_cache.dosing_units_by_ingredient_id,
    )
