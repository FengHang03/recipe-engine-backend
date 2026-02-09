"""
L1 Recipe Generator API
FastAPI 服务，提供食材组合生成接口
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import logging
import os

# 导入 L1 组件
from l1_recipe_generator import L1RecipeGenerator
from l1_config import L1Config
from data_loader import IngredientDataLoader
from db_config import get_database_engine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# FastAPI 应用初始化
# ==========================================

app = FastAPI(
    title="L1 Recipe Generator API",
    description="宠物食谱食材组合生成服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置（根据需要调整）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 全局状态
# ==========================================

class AppState:
    """应用状态（单例模式）"""
    def __init__(self):
        self.db_engine = None
        self.data_loader = None
        self.ingredients_df = None
        self.l1_generator = None
        self.is_initialized = False

app_state = AppState()


# ==========================================
# Pydantic 模型
# ==========================================

class DogProfile(BaseModel):
    """狗的配置信息"""
    name: Optional[str] = "My Dog"
    weight_kg: float = Field(..., gt=0, description="体重（公斤）")
    age_years: int = Field(..., ge=0, description="年龄（岁）")
    conditions: List[str] = Field(
        default_factory=list,
        description="健康状况列表，如: ['hyperlipidemia', 'kidney_disease']"
    )
    allergies: List[str] = Field(
        default_factory=list,
        description="过敏原列表，如: ['chicken', 'beef']"
    )


class RecipeGenerationRequest(BaseModel):
    """食谱生成请求"""
    dog_profile: DogProfile
    max_combinations: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="最大组合数"
    )
    custom_config: Optional[Dict] = Field(
        default=None,
        description="自定义 L1 配置（可选）"
    )


class IngredientInfo(BaseModel):
    """食材信息"""
    ingredient_id: str
    description: str
    short_name: str
    food_group: str
    food_subgroup: str
    tags: List[str]


class CombinationInfo(BaseModel):
    """组合信息"""
    combination_id: str
    ingredients: Dict[str, List[IngredientInfo]]
    diversity_score: float
    risk_score: float
    completeness_score: float
    active_slots: List[str]


class RecipeGenerationResponse(BaseModel):
    """食谱生成响应"""
    success: bool
    message: str
    combinations: List[CombinationInfo]
    total_combinations: int
    dog_profile: DogProfile


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str
    database_connected: bool
    ingredients_loaded: int
    version: str


# ==========================================
# 启动和关闭事件
# ==========================================

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    logger.info("=" * 60)
    logger.info("Starting L1 Recipe Generator API...")
    logger.info("=" * 60)
    
    try:
        # 1. 连接数据库
        logger.info("Step 1: Connecting to database...")
        app_state.db_engine = get_database_engine()
        
        # 2. 初始化数据加载器
        logger.info("Step 2: Initializing data loader...")
        app_state.data_loader = IngredientDataLoader(app_state.db_engine)
        
        # 3. 加载食材数据
        logger.info("Step 3: Loading ingredient data...")
        app_state.ingredients_df = app_state.data_loader.load_ingredients_for_l1()
        logger.info(f"  Loaded {len(app_state.ingredients_df)} ingredients")
        
        # 4. 初始化 L1 生成器
        logger.info("Step 4: Initializing L1 generator...")
        app_state.l1_generator = L1RecipeGenerator(app_state.ingredients_df)
        
        app_state.is_initialized = True
        logger.info("=" * 60)
        logger.info("✅ L1 Recipe Generator API started successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        app_state.is_initialized = False
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    logger.info("Shutting down L1 Recipe Generator API...")
    
    if app_state.db_engine:
        app_state.db_engine.dispose()
        logger.info("Database connection closed")


# ==========================================
# API 端点
# ==========================================

@app.get("/", response_model=dict)
async def root():
    """根端点"""
    return {
        "service": "L1 Recipe Generator API",
        "version": "1.0.0",
        "status": "running" if app_state.is_initialized else "initializing",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """健康检查端点"""
    return HealthCheckResponse(
        status="healthy" if app_state.is_initialized else "unhealthy",
        database_connected=app_state.db_engine is not None,
        ingredients_loaded=len(app_state.ingredients_df) if app_state.ingredients_df is not None else 0,
        version="1.0.0"
    )


@app.post("/generate", response_model=RecipeGenerationResponse)
async def generate_recipe_combinations(request: RecipeGenerationRequest):
    """
    生成食材组合
    
    主要流程：
    1. 验证请求参数
    2. 应用狗的配置（健康状况、过敏等）
    3. 调用 L1 生成器
    4. 返回候选组合
    """
    if not app_state.is_initialized:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized. Please try again later."
        )
    
    try:
        logger.info(f"Generating combinations for dog: {request.dog_profile.name}")
        logger.info(f"  Weight: {request.dog_profile.weight_kg}kg")
        logger.info(f"  Conditions: {request.dog_profile.conditions}")
        logger.info(f"  Allergies: {request.dog_profile.allergies}")
        
        # 转换 dog_profile 为字典
        dog_profile_dict = {
            'name': request.dog_profile.name,
            'weight_kg': request.dog_profile.weight_kg,
            'age_years': request.dog_profile.age_years,
            'conditions': request.dog_profile.conditions,
            'allergies': request.dog_profile.allergies
        }
        
        # 调用 L1 生成器
        combinations = app_state.l1_generator.generate(
            max_combinations=request.max_combinations,
            dog_profile=dog_profile_dict
        )
        
        # 转换为响应格式
        combination_infos = []
        for combo in combinations:
            # 转换 ingredients
            ingredients_dict = {}
            for slot_name, ing_list in combo.ingredients.items():
                ingredients_dict[slot_name] = [
                    IngredientInfo(
                        ingredient_id=ing.ingredient_id,
                        description=ing.description,
                        short_name=ing.short_name,
                        food_group=ing.food_group,
                        food_subgroup=ing.food_subgroup,
                        tags=ing.tags
                    )
                    for ing in ing_list
                ]
            
            combination_infos.append(
                CombinationInfo(
                    combination_id=combo.combination_id,
                    ingredients=ingredients_dict,
                    diversity_score=combo.diversity_score,
                    risk_score=combo.risk_score,
                    completeness_score=combo.completeness_score,
                    active_slots=combo.active_slots
                )
            )
        
        logger.info(f"✅ Generated {len(combinations)} combinations")
        
        return RecipeGenerationResponse(
            success=True,
            message=f"Successfully generated {len(combinations)} combinations",
            combinations=combination_infos,
            total_combinations=len(combinations),
            dog_profile=request.dog_profile
        )
        
    except Exception as e:
        logger.error(f"Error generating combinations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate combinations: {str(e)}"
        )


@app.get("/ingredients", response_model=dict)
async def list_ingredients(
    food_group: Optional[str] = Query(None, description="按食材大类过滤"),
    food_subgroup: Optional[str] = Query(None, description="按食材子类过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制")
):
    """
    列出食材
    可以按食材分类过滤
    """
    if not app_state.is_initialized:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        df = app_state.ingredients_df.copy()
        
        # 应用过滤
        if food_group:
            df = df[df['food_group'] == food_group]
        
        if food_subgroup:
            df = df[df['food_subgroup'] == food_subgroup]
        
        # 限制返回数量
        df = df.head(limit)
        
        # 转换为字典列表
        ingredients = df.to_dict('records')
        
        return {
            "total": len(ingredients),
            "food_group": food_group,
            "food_subgroup": food_subgroup,
            "ingredients": ingredients
        }
        
    except Exception as e:
        logger.error(f"Error listing ingredients: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=dict)
async def get_statistics():
    """获取系统统计信息"""
    if not app_state.is_initialized:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        df = app_state.ingredients_df
        
        stats = {
            "total_ingredients": len(df),
            "food_groups": df['food_group'].value_counts().to_dict(),
            "food_subgroups": df['food_subgroup'].value_counts().head(20).to_dict(),
            "tags_distribution": {}
        }
        
        # 统计标签
        all_tags = []
        for tags_list in df['tags']:
            if isinstance(tags_list, list):
                all_tags.extend(tags_list)
        
        from collections import Counter
        tag_counter = Counter(all_tags)
        stats['tags_distribution'] = dict(tag_counter.most_common(20))
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 错误处理
# ==========================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "success": False,
        "error": str(exc),
        "detail": "An unexpected error occurred"
    }


# ==========================================
# 运行（仅用于本地测试）
# ==========================================

if __name__ == "__main__":
    import uvicorn
    
    # 本地开发模式
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=True,
        log_level="info"
    )