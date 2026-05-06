"""
main.py
FastAPI 后端入口 — 演示版（同步）
路径：backend/app/main.py
Cloud Run 部署时必须调高超时时间：
  gcloud run services update YOUR_SERVICE \
    --timeout=600 \
    --region=us-central1 \
    --concurrency=4

本地启动（在 backend/ 目录下）：
  uvicorn main:app --host 0.0.0.0 --port 8080 --reload
"""

import logging
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional, Dict

from dotenv import load_dotenv

ENV_FILE = Path(__file__).parent.parent / ".env"

if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ── 业务组件 ──────────────────────────────────────────────────
from app.common.enums import (
    LifeStage, NutrientID,
)
from app.db.connection import create_db_engine, dispose_engine

from app.domains.ingredients.infra.ingredient_data_cache import IngredientDataCache
from app.domains.ingredients.infra.ingredient_repository import IngredientRepository
from app.domains.ingredients.infra.ingredient_nutrients_repository import IngredientNutrientsRepository

from app.database.data_loader import IngredientDataLoader
from app.L1Generator.l1_recipe_generator import L1RecipeGenerator
from app.L2Generator.l2_optimizer import L2Optimizer
from app.L2Generator.l2_data_models import PetProfile, OptimizationResult
from app.recipe_engine import RecipeEngine

# ── Explain Router ───────────────────────────────────────────
from app.api.api_router import api_router

# ==========================================
# 日志
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# ==========================================
# 全局应用状态（服务启动时初始化一次）
# ==========================================

class AppState:
    def __init__(self):
        self.data_loader: Optional[IngredientDataLoader] = None
        self.ingredients_df = None
        self.l1_generator: Optional[L1RecipeGenerator] = None
        self.l2_optimizer: Optional[L2Optimizer] = None
        self.recipe_engine: Optional[RecipeEngine] = None
        self.is_initialized: bool = False

app_state = AppState()


# ==========================================
# Lifespan：启动时初始化所有组件
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"🚀 Deploy Recipe Service ... env={ENVIRONMENT}")
    logger.info("=" * 60)

    try:
        engine = create_db_engine()

        ingredient_cache = IngredientDataCache.load_from_db(engine)

        app.state.db_engine = engine
        app.state.ingredient_data_cache = ingredient_cache
        app.state.ingredient_repository = IngredientRepository(
            engine=engine,
            data_cache=ingredient_cache,
        )
        app.state.ingredient_nutrients_repository = IngredientNutrientsRepository(
            engine=engine,
            data_cache=ingredient_cache,
        )

        db_url = _build_db_url()

        logger.info("[1/4] 初始化数据加载器...")
        app_state.data_loader = IngredientDataLoader(connection_string=db_url)

        logger.info("[2/4] 加载食材数据...")
        app_state.ingredients_df = await asyncio.to_thread(
            app_state.data_loader.load_ingredients_for_l1
        )
        logger.info(f"      ✅ 共加载 {len(app_state.ingredients_df)} 条食材")

        logger.info("[3/4] 构建 L1 生成器...")
        app_state.l1_generator = L1RecipeGenerator(app_state.ingredients_df)

        logger.info("[4/4] 构建 L2 优化器 & Recipe Engine...")
        app_state.l2_optimizer = L2Optimizer()
        app_state.recipe_engine = RecipeEngine(
            data_loader=app_state.data_loader,
            l1_generator=app_state.l1_generator,
            l2_optimizer=app_state.l2_optimizer,
        )

        app_state.is_initialized = True
        logger.info("✅ 服务启动成功！")

    except Exception as e:
        logger.error(f"❌ 服务启动失败：{e}", exc_info=True)
        raise

    yield

    logger.info("服务关闭")
    dispose_engine(engine)


def _build_db_url() -> str:
    if ENVIRONMENT == "production":
        instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")
        user = os.environ.get("DB_USER")
        password = os.environ.get("DB_PASSWORD")
        db_name = os.environ.get("DB_NAME")

        missing = [
            name for name, value in {
                "INSTANCE_CONNECTION_NAME": instance_connection_name,
                "DB_USER": user,
                "DB_PASSWORD": password,
                "DB_NAME": db_name,
            }.items() if not value
        ]

        if missing:
            raise RuntimeError(f"缺少生产环境变量: {', '.join(missing)}")

        socket = f"/cloudsql/{instance_connection_name}/.s.PGSQL.5432"
        return f"postgresql+pg8000://{user}:{password}@/{db_name}?unix_sock={socket}"
    else:
        host = os.environ.get("DB_HOST", "127.0.0.1")
        port = os.environ.get("DB_PORT", "15432")
        user = os.environ.get("DB_USER", "postgres")
        password = os.environ.get("DB_PASSWORD", "")
        db_name = os.environ.get("DB_NAME", "tuanty_recipe")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"


# ==========================================
# FastAPI 应用
# ==========================================

app = FastAPI(
    title="Pet Recipe Generator API (Demo)",
    version="1.0.0-demo",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 演示版开放所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 explain router

app.include_router(api_router)

# ==========================================
# Pydantic 模型
# ==========================================

# ── EnergyCalculator ──────────────────────

class EnergyRequest(BaseModel):
    weight_kg: float = Field(..., gt=0)
    species: str
    age_months: int = Field(..., ge=1)
    activity_level: str
    sterilization_status: str
    reproductive_stage: str
    breed: Optional[str] = None
    lactation_week: int = 4
    nursing_count: int = 1
    senior_month: Optional[int] = None


class EnergyResponse(BaseModel):
    resting_energy_kcal: float
    daily_energy_kcal: float
    life_stage: str
    model_version: str
    calculation_breakdown: Dict[str, float]
    warnings: List[str]


# ── 食谱生成 ──────────────────────────────

class PetProfileRequest(BaseModel):
    daily_calories_kcal: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    life_stage: str
    size_class: Optional[str] = "medium"
    activity_level: Optional[str] = None
    health_conditions: List[str] = []
    sterilization_status: Optional[str] = "intact"
    reproductive_stage: Optional[str] = None
    allergies: Optional[List[str]] = []
    species: str = "dog"
    breed: Optional[str] = None
    age_months: Optional[int] = 12


class GenerateRequest(BaseModel):
    pet: PetProfileRequest
    top_k: int = Field(default=5, ge=1, le=20)


# ── 食谱结果 ──────────────────────────────

class NutrientAnalysisOut(BaseModel):
    nutrient_id: str
    nutrient_name: str
    value: Optional[float]
    unit: Optional[str]
    min_required: Optional[float]
    max_allowed: Optional[float]
    ideal_target: Optional[float]
    meets_min: bool
    meets_max: bool
    deviation_from_ideal: Optional[float]


class OptimizedWeightOut(BaseModel):
    ingredient_id: str
    ingredient_name: str
    weight_grams: float
    percentage: float   # 占总重量百分比，后端计算
    is_supplement: bool
    slot_name: Optional[str]


class RecipeOut(BaseModel):
    rank: int
    recipe_id: str
    total_weight_grams: float
    objective_value: Optional[float]
    used_supplements: List[str]
    weights: List[OptimizedWeightOut]
    nutrient_analysis: List[NutrientAnalysisOut]


class GenerateResponse(BaseModel):
    """同步版：直接返回食谱列表"""
    success: bool
    total: int
    recipes: List[RecipeOut]
    elapsed_seconds: float


# ==========================================
# 工具函数
# ==========================================

def _check_initialized():
    if not app_state.is_initialized:
        raise HTTPException(status_code=503, detail="服务正在初始化，请稍后重试")


def _parse_life_stage(s: str) -> LifeStage:
    try:
        return LifeStage[s.upper()]
    except KeyError:
        valid = [e.name for e in LifeStage]
        raise HTTPException(
            status_code=422,
            detail=f"life_stage '{s}' 无效，合法值：{valid}",
        )


def _serialize_results(results: List[OptimizationResult]) -> List[RecipeOut]:
    """
    将 List[OptimizationResult] 序列化为响应模型列表
    nutrient_id IntEnum → 小写字符串（如 "protein"）
    """
    output = []
    for rank, result in enumerate(results, start=1):
        total = result.total_weight_grams or 1.0

        weights_out = []
        if result.weights:
            for w in sorted(result.weights, key=lambda x: x.weight_grams, reverse=True):
                weights_out.append(OptimizedWeightOut(
                    ingredient_id=str(w.ingredient_id),
                    ingredient_name=w.ingredient_name,
                    weight_grams=round(w.weight_grams, 2),
                    percentage=round(w.weight_grams / total * 100, 2),
                    is_supplement=w.is_supplement,
                    slot_name=w.slot_name,
                ))

        nutrients_out = []
        if result.nutrient_analysis:
            for n in result.nutrient_analysis:
                if isinstance(n.nutrient_id, int):
                    try:
                        nid = NutrientID(n.nutrient_id).name.lower()
                    except ValueError:
                        nid = str(n.nutrient_id)
                else:
                    nid = str(n.nutrient_id).lower()

                nutrients_out.append(NutrientAnalysisOut(
                    nutrient_id=nid,
                    nutrient_name=n.nutrient_name,
                    value=round(float(n.value), 4) if n.value is not None else None,
                    unit=n.unit,
                    min_required=float(n.min_required) if n.min_required is not None else None,
                    max_allowed=float(n.max_allowed) if n.max_allowed is not None else None,
                    ideal_target=float(n.ideal_target) if n.ideal_target is not None else None,
                    meets_min=n.meets_min,
                    meets_max=n.meets_max,
                    deviation_from_ideal=float(n.deviation_from_ideal) if n.deviation_from_ideal is not None else None,
                ))

        output.append(RecipeOut(
            rank=rank,
            recipe_id=result.recipe_id,
            total_weight_grams=round(total, 2),
            objective_value=result.objective_value,
            used_supplements=result.used_supplements or [],
            weights=weights_out,
            nutrient_analysis=nutrients_out,
        ))
    return output


# ==========================================
# API 路由
# ==========================================

@app.get("/", tags=["通用"])
async def root():
    return {
        "service": "Pet Recipe Generator API",
        "version": "1.0.0-demo",
        "environment": ENVIRONMENT,
        "status": "ready" if app_state.is_initialized else "initializing",
    }


@app.get("/health", tags=["通用"])
async def health():
    return {
        "status": "healthy" if app_state.is_initialized else "unhealthy",
        "ingredients_loaded": (
            len(app_state.ingredients_df)
            if app_state.ingredients_df is not None else 0
        ),
    }


# ──────────────────────────────────────────
# 能量计算（同步）
# ──────────────────────────────────────────

# @app.post("/api/calculate-energy", response_model=EnergyResponse, tags=["能量计算"])
# async def calculate_energy(request: EnergyRequest):
#     """计算宠物每日能量需求，AddPetForm 表单变化时自动调用"""
#     try:
#         result = EnergyCalculator.calculate_daily_energy_requirement(
#             weight_kg=request.weight_kg,
#             species=Species(request.species),
#             age_months=request.age_months,
#             activity_level=ActivityLevel(request.activity_level),
#             sterilization_status=SterilizationStatus(request.sterilization_status),
#             reproductive_stage=ReproductiveStage(request.reproductive_stage),
#             breed=request.breed,
#             lactation_week=request.lactation_week,
#             nursing_count=request.nursing_count,
#             senior_month=request.senior_month,
#         )
#         return EnergyResponse(
#             resting_energy_kcal=result.resting_energy_kcal,
#             daily_energy_kcal=result.daily_energy_kcal,
#             life_stage=result.life_stage,
#             model_version=result.model_version,
#             calculation_breakdown=result.calculation_breakdown,
#             warnings=result.warnings,
#         )
#     except ValueError as e:
#         raise HTTPException(status_code=422, detail=str(e))
#     except Exception as e:
#         logger.error(f"能量计算异常：{e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"能量计算失败：{str(e)}")


# ──────────────────────────────────────────
# 食谱生成（同步，直接返回结果）
# ──────────────────────────────────────────

@app.post("/recipes/generate", response_model=GenerateResponse, tags=["食谱生成"])
async def generate_recipes(request: GenerateRequest):
    """
    同步生成食谱，直接返回完整结果。

    注意：此接口会阻塞 1-3 分钟，Cloud Run 需要设置足够的超时时间：
      gcloud run services update YOUR_SERVICE --timeout=600 --region=us-central1
    """
    _check_initialized()

    life_stage = _parse_life_stage(request.pet.life_stage)

    pet = PetProfile(
        daily_calories_kcal=request.pet.daily_calories_kcal,
        weight_kg=request.pet.weight_kg,
        life_stage=life_stage,
        allergies=request.pet.allergies,
        size_class=request.pet.size_class,
        activity_level=request.pet.activity_level,
        health_conditions=request.pet.health_conditions,
        sterilization_status=request.pet.sterilization_status,
    )

    logger.info(
        f"[generate] 开始计算 life_stage={life_stage.name}, "
        f"weight={request.pet.weight_kg}kg, "
        f"calories={request.pet.daily_calories_kcal}kcal, "
        f"top_k={request.top_k}"
    )

    import time
    start = time.perf_counter()

    try:
        results: List[OptimizationResult] = await asyncio.to_thread(
            app_state.recipe_engine.generate_recipes,
            pet,
            request.top_k,
        )
    except Exception as e:
        logger.error(f"[generate] 计算异常：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"食谱生成失败：{str(e)}")

    elapsed = round(time.perf_counter() - start, 2)
    logger.info(f"[generate] 计算完成，耗时={elapsed}s，结果数={len(results)}")

    recipes = _serialize_results(results)

    return GenerateResponse(
        success=True,
        total=len(recipes),
        recipes=recipes,
        elapsed_seconds=elapsed,
    )


# ==========================================
# 全局异常兜底
# ==========================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"未处理异常：{exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)},
    )


# ==========================================
# 本地运行入口
# ==========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=False,
        log_level="info",
    )