# app/api/router.py

from fastapi import APIRouter
from pandas import api
from app.api.router.recipe import router as recipe_generate_router
from app.api.router.recipe_chat import router as recipe_chat_router
from app.api.router.energy import router as energy_router
from app.api.router.ingredients import router as ingredients_router
from app.api.router.explain import router as explain_router
# from app.api.router.xxx import router as xxx_router

api_router = APIRouter(prefix="/api")

api_router.include_router(recipe_generate_router)
api_router.include_router(recipe_chat_router)
api_router.include_router(energy_router)
api_router.include_router(ingredients_router)
api_router.include_router(explain_router)
# api_router.include_router(xxx_router)