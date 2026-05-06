from typing import Any, List, Dict, Set, Union, Optional

from app.shared.contracts.enums import(
 NutrientID, LifeStage, SlotType
)
from app.domains.recipe_generation.contracts.constraints import(
    NutrientConstraint, SlotConstraint, FoodGroup, SubgroupConstraint,
    RiskTagConstraint, MutualExclusionRule
)

# ==================== 槽位约束配置 ====================

SLOT_CONSTRAINTS: Dict[SlotType, SlotConstraint] = {
    SlotType.MAIN_PROTEIN: SlotConstraint(
        slot=SlotType.MAIN_PROTEIN,
        min_ratio=0.25,      # 硬最小值降低 (从 0.40 → 0.30)
        max_ratio=0.80,      # 硬最大值
        ideal_min=0.40,      # 理想最小值 (通过罚分引导)
        ideal_max=0.50       # 理想最大值
    ),
    
    SlotType.ORGAN_LIVER: SlotConstraint(
        slot=SlotType.ORGAN_LIVER,
        min_ratio=0.00,      # 不设硬最小值 (允许无肝脏的配方)
        max_ratio=0.05,      # 硬最大值: 严格限制 6%
        ideal_min=0.03,      # 理想: 3-5%
        ideal_max=0.05
    ),
    
    SlotType.ORGAN_SECRETING: SlotConstraint(
        slot=SlotType.ORGAN_SECRETING,
        min_ratio=0.00,
        max_ratio=0.05,      # 分泌型器官: 限制 7%
        ideal_min=0.03,
        ideal_max=0.05
    ),
    
    SlotType.ORGAN_MUSCULAR: SlotConstraint(
        slot=SlotType.ORGAN_MUSCULAR,
        min_ratio=0.00,
        max_ratio=0.15,      # 肌肉型器官: 适量
        ideal_min=0.05,
        ideal_max=0.10
    ),
    
    SlotType.MINERAL_SHELLFISH: SlotConstraint(
        slot=SlotType.MINERAL_SHELLFISH,
        min_ratio=0.00,
        max_ratio=0.05,      # 贝类: 补微量元素
        ideal_min=0.00,
        ideal_max=0.03
    ),
    
    SlotType.VEGETABLE: SlotConstraint(
        slot=SlotType.VEGETABLE,
        min_ratio=0.00,
        max_ratio=0.10,      # 蔬菜: 纤维来源
        ideal_min=0.05,
        ideal_max=0.08
    ),
    
    SlotType.CARBOHYDRATE: SlotConstraint(
        slot=SlotType.CARBOHYDRATE,
        min_ratio=0.00,
        max_ratio=0.25,      # 碳水: 可选
        ideal_min=0.00,
        ideal_max=0.15
    ),
    
    SlotType.OMEGA3_LC: SlotConstraint(
        slot=SlotType.OMEGA3_LC,
        min_ratio=0.00,
        max_ratio=0.03,      # 鱼油: 极少量
        ideal_min=0.005,
        ideal_max=0.02
    ),
    
    SlotType.OMEGA6_LA: SlotConstraint(
        slot=SlotType.OMEGA6_LA,
        min_ratio=0.00,
        max_ratio=0.03,      # 植物油: 极少量
        ideal_min=0.00,
        ideal_max=0.02
    ),
    
    SlotType.SUPPLEMENT: SlotConstraint(
        slot=SlotType.SUPPLEMENT,
        min_ratio=0.00,
        max_ratio=0.02,      # 补剂 (不含钙粉): 兜底
        ideal_min=0.00,
        ideal_max=0.01
    ),
    
    SlotType.SUPPLEMENT_CALCIUM: SlotConstraint(
        slot=SlotType.SUPPLEMENT_CALCIUM,
        min_ratio=0.00,
        max_ratio=0.90,      # 钙粉单独计算: 最多 5%
        ideal_min=0.00,
        ideal_max=0.00
    ),
    
    SlotType.IODINE: SlotConstraint(
        slot=SlotType.IODINE,
        min_ratio=0.00,
        max_ratio=0.01,      # 碘源: 极微量
        ideal_min=0.00,
        ideal_max=0.005
    ),

    SlotType.EGG: SlotConstraint(
        slot=SlotType.EGG,
        min_ratio=0.00,
        max_ratio=0.10,      
        ideal_min=0.00,
        ideal_max=0.10
    ),

    SlotType.SHELLFISH_PROTEIN: SlotConstraint(
        slot=SlotType.SHELLFISH_PROTEIN,
        min_ratio=0.20,
        max_ratio=0.40,      
        ideal_min=0.20,
        ideal_max=0.30
    ),

    SlotType.SHELLFISH_MINERAL: SlotConstraint(
        slot=SlotType.SHELLFISH_MINERAL,
        min_ratio=0.10,
        max_ratio=0.20,     
        ideal_min=0.10,
        ideal_max=0.20
    )
}


# ==================== 子类特殊约束 ====================

SUBGROUP_CONSTRAINTS: Dict[str, SubgroupConstraint] = {
    # 特定器官的额外限制
    "organ_spleen": SubgroupConstraint(
        subgroup="organ_spleen",
        max_ratio=0.05,   # 脾脏: 防腹泻
        reason="The spleen has a very high iron content, and excessive intake may lead to soft stool"
    ),
    "organ_brain": SubgroupConstraint(
        subgroup="organ_brain",
        max_ratio=0.05,
        reason="The cholesterol content in brain tissue is high and should not be excessive"
    ),
    "organ_kidney": SubgroupConstraint(
        subgroup="organ_kidney",
        max_ratio=0.06,
        reason="The content of vitamin A in the kidneys is relatively high"
    ),
    "supplement_calcium": SubgroupConstraint(
        subgroup="supplement_calcium",
        max_ratio=0.02,
        reason="Prioritize obtaining calcium from natural ingredients"
    )
}


# ==================== 风险标签约束 ====================

RISK_TAG_CONSTRAINTS: Dict[str, RiskTagConstraint] = {
    "risk_high_iodine": RiskTagConstraint(
        tag="risk_high_iodine",
        max_ratio=0.002,     # 0.2% (海带/海藻粉)
        reason="海带/海藻粉碘含量极高 (1000-3000 mg/100g),过量会导致甲状腺功能紊乱"
    ),
    
    "risk_high_vit_a": RiskTagConstraint(
        tag="risk_high_vit_a",
        max_ratio=0.05,      # 5% (反刍动物肝脏)
        reason="反刍动物肝脏维生素A含量极高,过量会导致骨骼畸形和肝损伤"
    ),
    
    "risk_laxative": RiskTagConstraint(
        tag="risk_laxative",
        max_ratio=0.05,      # 5% (脾脏/胰腺)
        reason="脾脏和胰腺含有大量消化酶和血液,过量会导致软便或腹泻"
    ),
    
    "risk_high_oxalate": RiskTagConstraint(
        tag="risk_high_oxalate",
        max_ratio=0.03,      # 3% (菠菜/甜菜)
        reason="草酸含量高的蔬菜会与钙结合形成草酸钙结石"
    ),
    
    "risk_expands": RiskTagConstraint(
        tag="risk_expands",
        max_ratio=0.01,      # 1% (洋车前子壳)
        reason="吸水后体积膨胀5-10倍,过量可能导致肠梗阻"
    ),
    
    "risk_high_purine": RiskTagConstraint(
        tag="risk_high_purine",
        max_ratio=0.10,      # 10% (内脏/沙丁鱼)
        reason="高嘌呤食材过多可能增加尿酸水平,对肾脏有负担"
    ),
    
    "risk_goitrogen": RiskTagConstraint(
        tag="risk_goitrogen",
        max_ratio=0.05,      # 5% (甘蓝/花椰菜)
        reason="含致甲状腺肿物质,生食过多会干扰碘吸收"
    )
}


# ==================== 食材组合互斥规则 ====================

MUTUAL_EXCLUSION_RULES: Dict[str, MutualExclusionRule] = {
    # 钙源互斥 (不要同时用多种钙补剂)
    "calcium_sources": MutualExclusionRule(
        rule_id="calcium_sources",
        ingredient_ids=["bone_meal", "calcium_carbonate", "eggshell_powder"],
        max_count=1,
        reason="只需一种钙源,避免过度补充"
    ),
    
    # 鱼油互斥
    "fish_oil_sources": MutualExclusionRule(
        rule_id="fish_oil_sources",
        ingredient_ids=["fish_oil", "krill_oil", "algae_oil"],
        max_count=1,
        reason="只需一种 Omega-3 来源"
    ),
    
    # 碘源互斥
    "iodine_sources": MutualExclusionRule(
        rule_id="iodine_sources",
        ingredient_ids=["kelp", "dulse", "iodized_salt"],
        max_count=1,
        reason="碘源过多会相互叠加,增加中毒风险"
    )
}


# ==================== 辅助函数 ====================

def get_slot_constraint(slot: Union[SlotType, str]) -> SlotConstraint:
    """获取槽位约束（兼容字符串/枚举输入）"""
    try:
        slot_enum = SlotType(slot) if isinstance(slot, str) else slot
        return SLOT_CONSTRAINTS.get(slot_enum)
    except (ValueError, AttributeError):
        print(f"警告：槽位 '{slot}' 无效")
        return None

def get_risk_constraint(tag: str) -> RiskTagConstraint:
    """获取风险标签约束"""
    return RISK_TAG_CONSTRAINTS.get(tag)

def get_subgroup_constraint(subgroup: str) -> SubgroupConstraint:
    """新增：获取子组约束"""
    return SUBGROUP_CONSTRAINTS.get(subgroup)

def get_mutual_exclusion_rule(rule_id: str) -> MutualExclusionRule:
    """新增：获取互斥规则"""
    return MUTUAL_EXCLUSION_RULES.get(rule_id)

def get_slot_constraint(slot: str) -> SlotConstraint:
    """获取槽位约束"""
    try:
        slot_enum = SlotType(slot)
        constraint = SLOT_CONSTRAINTS.get(slot_enum)
        return constraint
    except ValueError as e:
        print(f"警告：槽位 '{slot}' 无效")
        return None

def get_ingredients_with_slot(ingredients: list, slot: SlotType) -> list:
    """获取指定槽位的所有食材"""
    return [ing for ing in ingredients if ing.slot == slot]


def get_ingredients_with_tag(ingredients: list, tag: str) -> list:
    """获取带有指定标签的所有食材"""
    return [ing for ing in ingredients if tag in ing.tags]


def check_mutual_exclusion(ingredients: list) -> list:
    """
    检查食材组合是否违反互斥规则
    
    Returns:
        违规列表 (空列表表示通过)
    """
    violations = []
    
    for rule_name, rule in MUTUAL_EXCLUSION_RULES.items():
        matched_ingredients = [
            ing for ing in ingredients 
            if ing.ingredient_id in rule["ingredients"]
        ]
        
        if len(matched_ingredients) > rule["max_count"]:
            violations.append({
                "rule": rule_name,
                "reason": rule["reason"],
                "ingredients": [ing.ingredient_id for ing in matched_ingredients]
            })
    
    return violations


def calculate_slot_ratios(weights: dict, ingredients: list) -> dict:
    """
    计算各槽位的重量占比
    
    Args:
        weights: {ingredient_id: weight_grams}
        ingredients: 食材列表
        
    Returns:
        {SlotType: ratio}
    """
    total_weight = sum(weights.values())
    if total_weight == 0:
        return {}
    
    slot_weights = {}
    for ing in ingredients:
        weight = weights.get(ing.ingredient_id, 0)
        slot_weights[ing.slot] = slot_weights.get(ing.slot, 0) + weight
    
    slot_ratios = {
        slot: weight / total_weight 
        for slot, weight in slot_weights.items()
    }
    
    return slot_ratios


def validate_slot_constraints(slot_ratios: dict) -> list:
    """
    验证槽位约束是否满足
    
    Returns:
        违规列表
    """
    violations = []
    
    for slot, ratio in slot_ratios.items():
        constraint = get_slot_constraint(slot)
        if not constraint:
            continue
        
        if ratio < constraint.min_ratio:
            violations.append({
                "slot": slot,
                "type": "min",
                "actual": ratio,
                "required": constraint.min_ratio
            })
        
        if ratio > constraint.max_ratio:
            violations.append({
                "slot": slot,
                "type": "max",
                "actual": ratio,
                "limit": constraint.max_ratio
            })
    
    return violations
