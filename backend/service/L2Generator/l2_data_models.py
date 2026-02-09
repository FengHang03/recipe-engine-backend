"""
L2 营养优化引擎 - 数据结构定义
Data Models for L2 Nutritional Optimization Engine

这个文件定义了 L2 层的所有输入输出数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import pandas as pd
import sys
from pathlib import Path
# 获取当前文件(l1_recipe_generator.py)的路径 → 上一级(L1Generator) → 上一级(service) → 上一级(backend)
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(BACKEND_DIR))

from service.common.enums import (
    LifeStage,
    FoodGroup,
    NutrientID,
)

from service.common.models import (
    RecipeCombination,
)

# ==================== 枚举定义 ====================

class SlotType(Enum):
    """食材槽位类型"""
    MAIN_PROTEIN = "main_protein"
    ORGAN_LIVER = "organ_liver"
    ORGAN_SECRETING = "organ_secreting"
    ORGAN_MUSCULAR = "organ_muscular"
    MINERAL_SHELLFISH = "mineral_shellfish"
    VEGETABLE = "vegetable"
    CARBOHYDRATE = "carbohydrate"
    OMEGA3_LC = "omega3_lc"
    OMEGA6_LA = "omega6_la"
    SUPPLEMENT = "supplement"
    SUPPLEMENT_CALCIUM = "supplement_calcium"
    IODINE = "iodine"


class SolveStatus(Enum):
    """求解状态"""
    OPTIMAL = "optimal"              # 最优解
    FEASIBLE = "feasible"            # 可行解 (非最优)
    INFEASIBLE = "infeasible"        # 不可行
    TIMEOUT = "timeout"              # 超时
    ERROR = "error"                  # 错误


class InfeasibilityReason(Enum):
    """不可行原因"""
    NUTRIENT_DEFICIT = "nutrient_deficit"      # 营养素不足 (Code 1001)
    TOXIC_CONFLICT = "toxic_conflict"          # 毒性冲突 (Code 1002)
    RATIO_CONFLICT = "ratio_conflict"          # 比率冲突 (Code 1003)
    SLOT_CONFLICT = "slot_conflict"            # 槽位冲突
    UNKNOWN = "unknown"


# ==================== 输入数据结构 ====================

@dataclass
class PetProfile:
    """宠物画像"""
    target_calories: float          # 目标热量 (kcal/day)
    body_weight: float              # 体重 (kg)
    life_stage: LifeStage           # 生命阶段
    
    # 可选字段
    allergies: List[str] = field(default_factory=list)
    size_class: Optional[str] = "medium"
    activity_level: Optional[str] = None
    health_conditions: List[str] = field(default_factory=list)


@dataclass
class Ingredient:
    """食材定义"""
    id: str                         # 唯一标识 (如 "chicken_breast")
    name: str                       # 显示名称
    slot: SlotType                  # 槽位类型
    
    # 营养成分 (per 100g)
    nutrients: Dict[str, float]     # {nutrient_id: value}
    calories_per_100g: float        # 热量 (kcal/100g)
    
    # 标签
    tags: List[str] = field(default_factory=list)  # 如 ["risk_high_vit_a"]
    category: Optional[str] = None  # 如 "poultry", "fish"
    
    # 补剂相关
    is_supplement: bool = False
    supplement_cost: float = 1.0    # 补剂的基础成本系数



@dataclass
class L2Input:
    """L2 引擎的完整输入"""
    pet_profile: PetProfile
    combination: RecipeCombination
    supplement_toolkit: List[Ingredient]  # 可用的补剂列表

    nutrient_matrix: pd.DataFrame
    nutrient_info: pd.DataFrame
    nutrient_conversion_factor: Dict[int, float]  # 单位转换器


# ==================== 输出数据结构 ====================

@dataclass
class OptimizedWeight:
    """优化后的食材重量"""
    ingredient_id: str
    ingredient_name: str
    weight_grams: float
    is_supplement: bool


@dataclass
class NutrientAnalysis:
    """营养分析报告"""
    nutrient_id: str
    nutrient_name: str
    value: float                    # 实际值
    unit: str                       # 单位
    
    # 约束情况
    min_required: Optional[float] = None
    max_allowed: Optional[float] = None
    ideal_target: Optional[float] = None
    
    # 达标情况
    meets_min: bool = True
    meets_max: bool = True
    deviation_from_ideal: Optional[float] = None


@dataclass
class InfeasibilityDiagnostic:
    """不可行性诊断"""
    reason: InfeasibilityReason
    conflicting_nutrients: List[str]
    bottleneck_constraint: Optional[str] = None
    suggestion: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """L2 优化结果"""
    # 求解状态
    status: SolveStatus
    solve_time_seconds: float
    
    # 如果成功
    weights: Optional[List[OptimizedWeight]] = None
    total_weight_grams: Optional[float] = None
    nutrient_analysis: Optional[List[NutrientAnalysis]] = None
    
    # 目标函数值
    objective_value: Optional[float] = None
    penalty_breakdown: Optional[Dict[str, float]] = None  # {toxic: x, balance: y, supplement: z}
    
    # 如果失败
    infeasibility_diagnostic: Optional[InfeasibilityDiagnostic] = None
    
    # 元数据
    combination_id: str = ""
    used_supplements: List[str] = field(default_factory=list)


# ==================== 配置结构 ====================

@dataclass
class NutrientConstraint:
    """营养素约束定义"""
    nutrient_id: str
    min: Optional[float] = None
    max: Optional[float] = None
    max_soft: Optional[float] = None  # 软上限 (通过罚分引导)
    max_hard: Optional[float] = None  # 硬上限 (绝对不可超)
    
    ideal: Optional[float] = None     # 理想目标值
    safe_target: Optional[float] = None    # 安全目标 (ALARA)
    warning_target: Optional[float] = None # 警戒值
    
    unit: str = ""
    priority: int = 1                 # 0=P0, 1=P1, 2=P2
    tolerance: float = 0.0            # 允许的误差比例
    
    # 罚分配置
    penalty_type: Optional[str] = None  # "alara", "balance", None
    penalty_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class SlotConstraint:
    """槽位约束定义"""
    slot: SlotType
    min_ratio: float = 0.0            # 占总重的最小比例
    max_ratio: float = 1.0            # 占总重的最大比例
    ideal_min: Optional[float] = None # 理想最小比例 (软约束)
    ideal_max: Optional[float] = None # 理想最大比例 (软约束)


@dataclass
class RiskTagConstraint:
    """风险标签约束"""
    tag: str                          # 如 "risk_high_iodine"
    max_ratio: float                  # 最大占比
    reason: str = ""


@dataclass
class WeightConfig:
    """目标函数权重配置"""
    toxic: float = 1e5                # 毒性罚分权重
    balance: float = 50               # 平衡罚分权重
    supplement: float = 1e3           # 补剂罚分权重
    
    # 补剂具体权重 (相对于 supplement)
    supplement_weights: Dict[str, float] = field(default_factory=lambda: {
        "kelp": 1.0,
        "zinc": 2.0,
        "vit_e": 3.0,
        "fish_oil": 4.0,
        "calcium": 5.0
    })


# ==================== 辅助函数 ====================

def get_nutrient_value(ingredient: Ingredient, nutrient_id: str) -> float:
    """
    安全地获取食材的营养素值
    
    Args:
        ingredient: 食材对象
        nutrient_id: 营养素 ID
        
    Returns:
        营养素值 (如果不存在返回 0.0)
    """
    return ingredient.nutrients.get(nutrient_id, 0.0)


def format_weight(weight_grams: float) -> str:
    """格式化重量显示"""
    if weight_grams < 1:
        return f"{weight_grams*1000:.1f}mg"
    else:
        return f"{weight_grams:.1f}g"


def calculate_total_calories(weights: List[OptimizedWeight], ingredients: Dict[str, Ingredient]) -> float:
    """
    计算总热量
    
    Args:
        weights: 优化后的重量列表
        ingredients: 食材字典 {id: Ingredient}
        
    Returns:
        总热量 (kcal)
    """
    total = 0.0
    for w in weights:
        ing = ingredients.get(w.ingredient_id)
        if ing:
            total += (w.weight_grams / 100) * ing.calories_per_100g
    return total