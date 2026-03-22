"""
L1 配置文件 - 最终版本
内脏分类: 采用 3-subgroup 方案 (ORGAN_LIVER / ORGAN_SECRETING / ORGAN_MUSCULAR)
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum

from sqlalchemy.sql.dml import ReturningInsert

# ========== 枚举定义 ==========

class FoodGroup(str, Enum):
    """食材大类"""
    PROTEIN_MEAT = "PROTEIN_MEAT"
    PROTEIN_FISH = "PROTEIN_FISH"
    PROTEIN_EGG = "PROTEIN_EGG"
    PROTEIN_SHELLFISH = "PROTEIN_SHELLFISH"
    MINERAL_SHELLFISH = "MINERAL_SHELLFISH"
    
    # 内脏 (3个组)
    ORGAN = "ORGAN"
    
    CARB_GRAIN = "CARB_GRAIN"
    CARB_TUBER = "CARB_TUBER"
    CARB_LEGUME = "CARB_LEGUME"
    CARB_OTHER = "CARB_OTHER"
    PLANT_ANTIOXIDANT = "PLANT_ANTIOXIDANT"
    FAT_OIL = "FAT_OIL"
    FIBER = "FIBER"
    SUPPLEMENT = "SUPPLEMENT"
    TREAT = "TREAT"
    DAIRY = "DAIRY"

class FoodSubgroup(str, Enum):
    """食材子类"""
    # 肉类
    MEAT_LEAN = "meat_lean"
    MEAT_MODERATE = "meat_moderate"
    MEAT_FAT = "meat_fat"
    
    # 鱼类
    FISH_LEAN = "fish_lean"
    FISH_OILY = "fish_oily"
    
    # 内脏 - 3-subgroup 方案
    # === ORGAN_LIVER 组 ===
    LIVER = "organ_liver"  # 肝脏 (鸡肝、牛肝、猪肝)
    
    # === ORGAN_SECRETING 组 ===
    KIDNEY = "organ_kidney"              # 肾脏
    SPLEEN = "organ_spleen"              # 脾脏
    BRAIN = "organ_brain"                # 脑花
    ORGAN_SECRETING = "organ_secreting"  # 胰腺、睾丸等
    
    # === ORGAN_MUSCULAR 组 ===
    HEART = "heart"                     # 心脏
    GIZZARD = "gizzard"                 # 胗 (鸡胗、鸭胗)
    ORGAN_MUSCULAR = "organ_muscular"   # 舌、肺、肚
    
    # 碳水
    CARB_GRAIN = "carb_grain"
    CARB_TUBER = "carb_tuber"
    CARB_LEGUME = "carb_legume"
    
    # 蔬菜
    PLANT_ORANGE = "plant_orange"  # 红/橙/黄色蔬菜
    PLANT_GREEN = "plant_green"    # 绿叶蔬菜
    PLANT_BLUE = "plant_blue"      # 蓝/紫色蔬菜
    PLANT_WHITE = "plant_white"    # 白色蔬菜
    
    # 其他
    FIBER_PLANT = "fiber_plant"
    FIBER_SUPPLEMENT = "supplement_fiber"
    OIL_OMEGA3_LC = "oil_omega3_lc"
    OIL_OMEGA6_LA = "oil_omega6_la"
    MINERAL_SHELLFISH = "mineral_shellfish"
    PROTEIN_SHELLFISH = "protein_shellfish"
    EGG = "egg"
    DAIRY = "dairy"
    SUPPLEMENT_CALCIUM = "supplement_calcium"
    SUPPLEMENT_IODINE = "supplement_iodine"
    SUPPLEMENT_OMEGA3 = "supplement_omega3_lc"
    SUPPLEMENT_OTHER = "supplement_other"

# ========== 筛选器定义 ==========

class IngredientFilter(BaseModel):
    """定义一个槽位允许放入什么样的食材"""
    allowed_groups: List[FoodGroup] = Field(default_factory=list)
    allowed_subgroups: List[FoodSubgroup] = Field(default_factory=list)
    required_tags: List[str] = Field(default_factory=list, description="必须包含的标签 (AND)")
    excluded_tags: List[str] = Field(default_factory=list, description="必须排除的标签 (NOT)")
    diversity_tags: List[str] = Field(default_factory=list, description="优先考虑的多样性标签")

# ========== 互斥规则定义 ==========

class ExclusionRule(BaseModel):
    """互斥规则 - 限制某些食材的选择"""
    rule_id: str
    target_subgroups: List[FoodSubgroup] = Field(default_factory=list)
    target_groups: List[FoodGroup] = Field(default_factory=list)
    target_tags: List[str] = Field(default_factory=list)
    max_count: int = 1
    max_total_weight_g: float | None = None
    reason: str = ""

# ========== 槽位定义 ==========

class SlotConfig(BaseModel):
    """定义槽位的静态属性"""
    name: str
    description: str = ""
    is_mandatory_default: bool = True
    initial_state: str = "optional"
    filters: IngredientFilter
    max_items: int = 1
    min_item: int = 0
    apply_diversity: bool = False
    # 槽位级别的约束
    min_weight_g: float | None = None
    max_weight_g: Optional[float] = None
    is_core_ingredient: bool = True

# ========== 依赖规则定义 ==========

class DependencyConfig(BaseModel):
    """定义槽位之间的动态依赖关系"""
    
    # Omega 逻辑
    skip_omega3_lc_if_oily_fish: bool = Field(
        default=True, 
        description="如果主肉含 role_omega3_lc 标签,跳过鱼油槽"
    )
    skip_omega6_la_if_fatty_meat: bool = Field(
        default=True,
        description="如果主肉含 role_omega6_la 标签,跳过植物油槽"
    )
    
    # 碳水逻辑
    force_carb_if_lean_protein: bool = Field(
        default=True,
        description="如果主蛋白是Lean,强制开启碳水"
    )
    allow_no_carb_if_fatty_protein: bool = Field(
        default=True,
        description="如果主蛋白脂肪含量>=Moderate,碳水可选"
    )
    
    # 纤维逻辑
    skip_fiber_if_carb_has_fiber: bool = Field(
        default=True,
        description="如果碳水含纤维,跳过纤维槽"
    )
    force_fiber_if_no_carb: bool = Field(
        default=True,
        description="如果没有碳水,强制开启纤维槽"
    )
    # 碘逻辑（新增 2026.02.03）
    skip_iodine_if_high_iodine_ingredient: bool = Field(
        default=True,
        description="如果已选食材含 risk_high_iodine,跳过碘槽"
    )
    
    # Shrimp 逻辑（新增 2026.02.03）
    force_main_protein_if_shellfish: bool = Field(
        default=True,
        description="如果选了贝类,强制选择主蛋白(肉/鱼)"
    )

    # optional ingredients logic
    choose_optional_ingredients: bool = Field(
        default=True,
        description="If current ingredients count < max ingredients count, choose optional ingredients"
    )

# ========== L1 总配置 ==========

class L1Config(BaseModel):
    """L1层总配置"""
    
    # A. 策略配置
    policies: DependencyConfig = Field(default_factory=DependencyConfig)
    
    # B. 互斥规则
    exclusion_rules: List[ExclusionRule] = Field(default_factory=lambda: [
        # 规则1: 内脏总量限制 - 肝脏和分泌型内脏加起来最多2种
        ExclusionRule(
            rule_id="organ_total_limit",
            target_subgroups=[
                FoodSubgroup.LIVER,
                FoodSubgroup.KIDNEY,
                FoodSubgroup.SPLEEN,
                FoodSubgroup.BRAIN,
                FoodSubgroup.ORGAN_SECRETING,
                FoodSubgroup.ORGAN_MUSCULAR,
            ],
            max_count=3,
            reason="肝脏和分泌型内脏总共最多2种"
        ),
        
        # 规则2: 肝脏单独限制 - 最多1个
        ExclusionRule(
            rule_id="liver_limit",
            target_subgroups=[FoodSubgroup.LIVER],
            max_count=1,
            reason="肝脏最多1种(维生素A风险)"
        ),

        # # 新增互斥规则：防止维A中毒
        # ExclusionRule(
        #     rule_id="avoid_vit_a_toxicity",
        #     # 目标：同时限制"高维A内脏"和"高维A油"
        #     target_tags=["risk_high_vit_a"], 
        #     max_count=1, # 整个配方中只能出现1个高维A食材
        #     reason="防止维生素A中毒(禁止 牛肝+鱼肝油 同时出现)"
        # )
    ])
    
    # C. 槽位配置
    slots: Dict[str, SlotConfig] = Field(default_factory=lambda: {
        # ========== 必选槽位 ==========
        "main_protein": SlotConfig(
            name="Main Protein Slot",
            is_mandatory_default=True,
            initial_state="mandatory",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.PROTEIN_MEAT, FoodGroup.PROTEIN_FISH],
                excluded_tags=["risk_high_copper"]
            ),
            apply_diversity=False,
            max_items=1,
            min_weight_g=100,
            is_core_ingredient=True,
        ),

        "shellfish_protein": SlotConfig(
            name="Shellfish Protein",
            is_mandatory_default=False,  # 默认关闭
            initial_state="optional",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.PROTEIN_SHELLFISH],
                excluded_tags=["protein_shellfish"]  # 不能再选贝类
            ),
            max_items=1,
            min_weight_g=50,
            is_core_ingredient=True,
        ),

        # 鸡蛋（必选 新增 2026.02.03）
        "egg": SlotConfig(
            name="Egg",
            is_mandatory_default=True,  # 必选
            initial_state="mandatory",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.PROTEIN_EGG]
            ),
            max_items=1,
            is_core_ingredient=True,
        ),
        
        "calcium": SlotConfig(
            name="Calcium Slot",
            is_mandatory_default=True,
            initial_state="mandatory",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.MINERAL_SHELLFISH, FoodGroup.SUPPLEMENT],
                allowed_subgroups=[
                    FoodSubgroup.MINERAL_SHELLFISH,
                    FoodSubgroup.SUPPLEMENT_CALCIUM
                ],
                required_tags=["role_calcium_source"]
            ),
            max_items=1,
            is_core_ingredient=True,
        ),

        "mineral_shellfish": SlotConfig(
            name="Mineral Shellfish",
            description="矿物质贝类（牡蛎、贻贝、蛤蜊等，微量元素补充）",
            initial_state="mandatory",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.MINERAL_SHELLFISH]
            ),
            max_items=1,
            is_core_ingredient=True,
        ),
        
        "organ_liver": SlotConfig(
            name="Organ Liver Slot",
            is_mandatory_default=True,
            initial_state="mandatory",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.ORGAN],
                allowed_subgroups=[FoodSubgroup.LIVER]
            ),
            apply_diversity=True,
            max_items=1,
            is_core_ingredient=True,
            max_weight_g=50,
        ),
        
        "organ_secreting": SlotConfig(
            name="Organ Secreting Slot",
            is_mandatory_default=False,
            initial_state="mandatory",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.ORGAN],
                allowed_subgroups=[
                    FoodSubgroup.KIDNEY,
                    FoodSubgroup.SPLEEN,
                    FoodSubgroup.BRAIN,
                    FoodSubgroup.ORGAN_SECRETING
                ]
            ),
            max_items=1,  # 可以选1-2种分泌型内脏
            is_core_ingredient=True,
            max_weight_g=100,
        ),
        
        "organ_muscular": SlotConfig(
            name="Organ Muscular Slot",
            is_mandatory_default=False,  # 可选
            initial_state="optional",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.ORGAN],
                allowed_subgroups=[
                    FoodSubgroup.HEART,
                    FoodSubgroup.GIZZARD,
                    FoodSubgroup.ORGAN_MUSCULAR
                ]
            ),
            max_items=2,  # 心脏等可以当肉用,允许多选
            is_core_ingredient=True,
        ),
        
        "vegetable": SlotConfig(
            name="Vegetable Slot",
            is_mandatory_default=True,
            initial_state="mandatory",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.PLANT_ANTIOXIDANT],
                allowed_subgroups=[
                    FoodSubgroup.PLANT_ORANGE,
                    FoodSubgroup.PLANT_GREEN,
                    FoodSubgroup.PLANT_BLUE,
                    FoodSubgroup.PLANT_WHITE
                ],
                diversity_tags=["div_plant_orange", "div_plant_green", "div_plant_blue"]
            ),
            apply_diversity=True,
            max_items=2,
            is_core_ingredient=True,
        ),
        
        # ========== 条件必选槽位 ==========
        "omega3_lc": SlotConfig(
            name="Omega3 LC Slot",
            is_mandatory_default=True,
            initial_state="mandatory",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.FAT_OIL, FoodGroup.SUPPLEMENT],
                allowed_subgroups=[
                    FoodSubgroup.OIL_OMEGA3_LC,
                    FoodSubgroup.SUPPLEMENT_OMEGA3
                ],
                required_tags=["role_omega3_lc"]
            ),
            max_items=1,
            is_core_ingredient=False,
            max_weight_g=10,
        ),
        
        "omega6_la": SlotConfig(
            name="Omega6 LA Slot",
            is_mandatory_default=True,
            initial_state="mandatory",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.FAT_OIL],
                allowed_subgroups=[FoodSubgroup.OIL_OMEGA6_LA],
                required_tags=["role_omega6_la"]
            ),
            max_items=1,
            is_core_ingredient=False,
            max_weight_g=10,
        ),
        
        # ========== 可选槽位 ==========
        "carbohydrate": SlotConfig(
            name="Carbohydrate Slot",
            is_mandatory_default=False,
            initial_state="optional",
            filters=IngredientFilter(
                allowed_groups=[
                    FoodGroup.CARB_GRAIN,
                    FoodGroup.CARB_TUBER,
                    FoodGroup.CARB_LEGUME
                ]
            ),
            max_items=1,
            min_item=0,
            max_weight_g=100,
            is_core_ingredient=True,
        ),

        "iodine": SlotConfig(
            name="Iodine Slot",
            is_mandatory_default=True,
            initial_state="mandatory",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.SUPPLEMENT],
                allowed_subgroups=[FoodSubgroup.SUPPLEMENT_IODINE],
            ),
            max_items=1,
            is_core_ingredient=False,
            max_weight_g=50,
        ),
        
        "fiber": SlotConfig(
            name="Fiber Slot",
            is_mandatory_default=False,
            initial_state="optional",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.FIBER, FoodGroup.SUPPLEMENT],
                allowed_subgroups=[
                    FoodSubgroup.FIBER_PLANT,
                    FoodSubgroup.FIBER_SUPPLEMENT
                ],
                required_tags=["role_fiber_source"]
            ),
            max_items=1,
            is_core_ingredient=False,
        ),

        "optional_ingredients": SlotConfig(
            name="Optional Ingredients Slot",
            is_mandatory_default=True,
            initial_state="optional",
            filters=IngredientFilter(
                allowed_groups=[FoodGroup.DAIRY, FoodGroup.TREAT],
            ),
            max_items=1,
            min_item=0,
            is_core_ingredient=False,
        ),
    })

def get_default_config() -> L1Config:
    return L1Config()

# ========== 内脏分类说明（文档用）==========

ORGAN_CLASSIFICATION_DOC = """
内脏分类方案 (3-subgroup)

1. ORGAN_LIVER (肝脏组)
   - Subgroup: liver
   - 包含: 鸡肝、牛肝、猪肝
   - L2约束: Max 5% (维生素A风险)
   - 示例营养: 维生素A 11,000 IU, 铜 0.5mg, 维生素B12 16µg

2. ORGAN_SECRETING (分泌型内脏组)
   - Subgroups: kidney, spleen, brain, other_secreting
   - 包含: 
     * kidney - 肾脏 (高B12、硒)
     * spleen - 脾脏 (铁45mg/100g ⚠️)
     * brain - 脑花 (胆固醇2000mg/100g ⚠️)
     * other_secreting - 胰腺、睾丸
   - L2约束: Max 5% (Combined - 这组总共最多5%)
   - 个体约束: 
     * spleen 建议 ≤3% (铁风险)
     * brain 建议 ≤3% (胆固醇风险)

3. ORGAN_MUSCULAR (肌肉型内脏组)
   - Subgroups: heart, gizzard, other_muscular
   - 包含:
     * heart - 心脏 (牛磺酸120mg, 辅酶Q10 11mg)
     * gizzard - 鸡胗、鸭胗
     * other_muscular - 舌、肺、肚
   - L2约束: No Limit (Count as Meat - 算作普通肉类蛋白)
   - 说明: 可以当肉用,不计入"内脏限制",但计入"蛋白质总量"

关键规则:
- 肝脏单独限制: 最多1种
- 肝脏+分泌型内脏: 总共最多2种
- 肌肉型内脏: 不限制,可多选
- L2会根据营养成分(铁、维A、硒等)进一步精确控制每种内脏的用量
"""


# ========== 使用示例 ==========

if __name__ == "__main__":
    config = L1Config()
    
    print("=" * 60)
    print("L1 配置 - 内脏分类方案 (3-subgroup)")
    print("=" * 60)
    
    print("\n【内脏分类说明】")
    print(ORGAN_CLASSIFICATION_DOC)
    
    print("\n【槽位配置】")
    for slot_name, slot_config in config.slots.items():
        print(f"\n{slot_name}:")
        print(f"  名称: {slot_config.name}")
        print(f"  默认启用: {slot_config.is_mandatory_default}")
        print(f"  最大数量: {slot_config.max_items}")
        if slot_config.filters.allowed_groups:
            print(f"  允许组: {[g.value for g in slot_config.filters.allowed_groups]}")
        if slot_config.filters.allowed_subgroups:
            print(f"  允许子类: {[sg.value for sg in slot_config.filters.allowed_subgroups]}")
    
    print("\n【互斥规则】")
    for rule in config.exclusion_rules:
        print(f"\n规则: {rule.rule_id}")
        if rule.target_groups:
            print(f"  目标组: {[g.value for g in rule.target_groups]}")
        if rule.target_subgroups:
            print(f"  目标子类: {[sg.value for sg in rule.target_subgroups]}")
        print(f"  最大数量: {rule.max_count}")
        print(f"  原因: {rule.reason}")