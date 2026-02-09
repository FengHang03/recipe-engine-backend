"""
槽位约束和风险标签配置
Slot Constraints and Risk Tag Configurations
"""

from .l2_data_models import SlotType, SlotConstraint, RiskTagConstraint


# ==================== 槽位约束配置 ====================

SLOT_CONSTRAINTS = {
    SlotType.MAIN_PROTEIN: SlotConstraint(
        slot=SlotType.MAIN_PROTEIN,
        min_ratio=0.30,      # 硬最小值降低 (从 0.40 → 0.30)
        max_ratio=0.90,      # 硬最大值
        ideal_min=0.40,      # 理想最小值 (通过罚分引导)
        ideal_max=0.70       # 理想最大值
    ),
    
    SlotType.ORGAN_LIVER: SlotConstraint(
        slot=SlotType.ORGAN_LIVER,
        min_ratio=0.00,      # 不设硬最小值 (允许无肝脏的配方)
        max_ratio=0.06,      # 硬最大值: 严格限制 6%
        ideal_min=0.03,      # 理想: 3-5%
        ideal_max=0.05
    ),
    
    SlotType.ORGAN_SECRETING: SlotConstraint(
        slot=SlotType.ORGAN_SECRETING,
        min_ratio=0.00,
        max_ratio=0.07,      # 分泌型器官: 限制 7%
        ideal_min=0.03,
        ideal_max=0.05
    ),
    
    SlotType.ORGAN_MUSCULAR: SlotConstraint(
        slot=SlotType.ORGAN_MUSCULAR,
        min_ratio=0.00,
        max_ratio=0.20,      # 肌肉型器官: 适量
        ideal_min=0.05,
        ideal_max=0.15
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
        max_ratio=0.15,      # 蔬菜: 纤维来源
        ideal_min=0.05,
        ideal_max=0.10
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
        max_ratio=0.05,      # 钙粉单独计算: 最多 5%
        ideal_min=0.00,
        ideal_max=0.02
    ),
    
    SlotType.IODINE: SlotConstraint(
        slot=SlotType.IODINE,
        min_ratio=0.00,
        max_ratio=0.01,      # 碘源: 极微量
        ideal_min=0.00,
        ideal_max=0.005
    )
}


# ==================== 子类特殊约束 ====================

SUBGROUP_CONSTRAINTS = {
    # 特定器官的额外限制
    "organ_spleen": {
        "max_ratio": 0.05,   # 脾脏: 防腹泻
        "reason": "脾脏含铁量极高,过量可能导致软便"
    },
    
    "organ_brain": {
        "max_ratio": 0.05,   # 脑花: 防胆固醇过高
        "reason": "脑组织胆固醇含量高,不宜过多"
    },
    
    "organ_kidney": {
        "max_ratio": 0.08,   # 肾脏: 适量
        "reason": "肾脏维生素A含量较高"
    },
    
    # 补剂的额外限制
    "supplement_calcium": {
        "max_ratio": 0.02,   # 钙粉: 防过度填充
        "reason": "优先从天然食材获取钙"
    }
}


# ==================== 风险标签约束 ====================

RISK_TAG_CONSTRAINTS = {
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

MUTUAL_EXCLUSION_RULES = {
    # 钙源互斥 (不要同时用多种钙补剂)
    "calcium_sources": {
        "ingredients": ["bone_meal", "calcium_carbonate", "eggshell_powder"],
        "max_count": 1,
        "reason": "只需一种钙源,避免过度补充"
    },
    
    # 鱼油互斥
    "fish_oil_sources": {
        "ingredients": ["fish_oil", "krill_oil", "algae_oil"],
        "max_count": 1,
        "reason": "只需一种 Omega-3 来源"
    },
    
    # 碘源互斥
    "iodine_sources": {
        "ingredients": ["kelp", "dulse", "iodized_salt"],
        "max_count": 1,
        "reason": "碘源过多会相互叠加,增加中毒风险"
    }
}


# ==================== 辅助函数 ====================

def get_slot_constraint(slot: SlotType) -> SlotConstraint:
    """获取槽位约束"""
    return SLOT_CONSTRAINTS.get(slot)


def get_risk_constraint(tag: str) -> RiskTagConstraint:
    """获取风险标签约束"""
    return RISK_TAG_CONSTRAINTS.get(tag)


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


# ==================== 验证函数 ====================

def validate_constraints():
    """验证约束配置的合理性"""
    issues = []
    
    # 检查槽位约束的合理性
    total_min = sum(c.min_ratio for c in SLOT_CONSTRAINTS.values())
    total_max = sum(c.max_ratio for c in SLOT_CONSTRAINTS.values())
    
    if total_min > 1.0:
        issues.append(f"Slot min ratios sum to {total_min:.2f} > 1.0")
    
    if total_max < 1.0:
        issues.append(f"Slot max ratios sum to {total_max:.2f} < 1.0")
    
    # 检查每个槽位的逻辑
    for slot, constraint in SLOT_CONSTRAINTS.items():
        if constraint.min_ratio > constraint.max_ratio:
            issues.append(f"{slot}: min_ratio > max_ratio")
        
        if constraint.ideal_min and constraint.ideal_min < constraint.min_ratio:
            issues.append(f"{slot}: ideal_min < min_ratio")
        
        if constraint.ideal_max and constraint.ideal_max > constraint.max_ratio:
            issues.append(f"{slot}: ideal_max > max_ratio")
    
    # 报告
    if issues:
        print("⚠️ Constraint Validation Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ Slot constraints validated successfully!")
        print(f"  Total min ratio: {total_min:.2f}")
        print(f"  Total max ratio: {total_max:.2f}")
    
    return len(issues) == 0


if __name__ == "__main__":
    validate_constraints()