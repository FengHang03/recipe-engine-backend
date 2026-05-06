# L2 营养优化引擎 — 接口文档

**版本**: v1.1（含 Bug 修复）  
**涉及文件**: `l2_optimizer.py` · `l2_aafco_config.py` · `l2_slot_config.py` · `l2_data_models.py`  
**求解器**: Google OR-Tools GLOP（线性规划）

---

## 目录

1. [系统概述](#系统概述)
2. [枚举类型](#枚举类型)
3. [输入数据结构](#输入数据结构)
   - [PetProfile](#petprofile)
   - [Ingredient](#ingredient)
   - [L2Input](#l2input)
4. [输出数据结构](#输出数据结构)
   - [OptimizationResult](#optimizationresult)
   - [OptimizedWeight](#optimizedweight)
   - [NutrientAnalysis](#nutrientanalysis)
   - [InfeasibilityDiagnostic](#infeasibilitydiagnostic)
5. [配置结构](#配置结构)
   - [NutrientConstraint](#nutrientconstraint)
   - [SlotConstraint](#slotconstraint)
   - [RiskTagConstraint](#risktagconstraint)
   - [WeightConfig](#weightconfig)
6. [L2Optimizer（主入口）](#l2optimizer主入口)
7. [AAFCO 营养标准（l2_aafco_config）](#aafco-营养标准)
8. [槽位与风险约束（l2_slot_config）](#槽位与风险约束)
9. [目标函数与罚分系统](#目标函数与罚分系统)
10. [两阶段求解策略](#两阶段求解策略)
11. [约束层级总览](#约束层级总览)
12. [使用示例](#使用示例)
13. [营养学说明](#营养学说明)
14. [修复记录 v1.1](#修复记录-v11)

---

## 系统概述

L2 层接收 L1 生成的食材组合，通过线性规划（LP）为每种食材求解最优用量（克数），使配方同时满足：

- **热量目标**：宠物每日所需卡路里（±5%）
- **AAFCO 营养标准**：34+ 种营养素的 Min/Max 约束（per 1000 kcal ME）
- **Ca:P 比率**：硬约束 0.8-2.5，软目标 1.0-2.0（理想 1.3）
- **槽位占比**：各食材类型的重量占比范围
- **风险标签**：高碘/高维A/泻药性食材的用量上限

**求解流程：**
```
L2Input ──► Phase 1（无补剂）──► OPTIMAL ──► 返回结果
                │
                ▼ INFEASIBLE
           Phase 2（带补剂）──► OPTIMAL / INFEASIBLE ──► 返回结果
```

---

## 枚举类型

### `SlotType`

食材槽位类型，用于槽位约束和食材分类。

| 值 | 含义 |
|----|------|
| `MAIN_PROTEIN` | 主蛋白（肉/鱼） |
| `ORGAN_LIVER` | 肝脏 |
| `ORGAN_SECRETING` | 分泌型内脏（肾/脾/脑） |
| `ORGAN_MUSCULAR` | 肌肉型内脏（心/胗） |
| `MINERAL_SHELLFISH` | 矿物质贝类（牡蛎等） |
| `VEGETABLE` | 蔬菜 |
| `CARBOHYDRATE` | 碳水化合物 |
| `OMEGA3_LC` | Omega-3 长链脂肪酸（鱼油） |
| `OMEGA6_LA` | Omega-6 亚油酸（植物油） |
| `SUPPLEMENT` | 通用补剂 |
| `SUPPLEMENT_CALCIUM` | 钙补剂（单独计算） |
| `IODINE` | 碘源 |
| `EGG` | 鸡蛋 |
| `SHELLFISH_PROTEIN` | 蛋白质贝类 |
| `SHELLFISH_MINERAL` | 矿物质贝类（别名） |
| `CALCIUM` | 钙源（天然食材） |

---

### `SolveStatus`

| 值 | 含义 |
|----|------|
| `OPTIMAL` | 最优解（目标函数全局最小） |
| `FEASIBLE` | 可行解（满足所有硬约束但非最优） |
| `INFEASIBLE` | 不可行（硬约束冲突，无解） |
| `TIMEOUT` | 超时（默认 100 秒限制） |
| `ERROR` | 求解器创建失败 |

---

### `InfeasibilityReason`

| 值 | 含义 |
|----|------|
| `NUTRIENT_DEFICIT` | 食材组合无法满足某营养素最低需求 |
| `TOXIC_CONFLICT` | 毒性元素上限与营养需求冲突 |
| `RATIO_CONFLICT` | Ca:P 等比率约束与食材结构冲突 |
| `SLOT_CONFLICT` | 槽位占比约束冲突 |
| `UNKNOWN` | 未知原因（待完善诊断系统） |

---

## 输入数据结构

### `PetProfile`

宠物画像，描述优化目标的基本参数。

```python
@dataclass
class PetProfile:
    daily_calories_kcal: float           # 每日目标热量（kcal/day）
    weight_kg: float               # 体重（kg）
    life_stage: LifeStage            # 生命阶段（决定 AAFCO 标准版本）
    allergies: List[str] = []        # 过敏原标签列表
    size_class: str = "medium"       # 体型（"toy"/"small"/"medium"/"large"/"giant"）
    activity_level: str = None       # 活动水平（预留，当前未使用）
    health_conditions: List[str] = [] # 健康状况（预留，当前未使用）
    sterilization_status: Optional[SterilizationStatus] = 'intact'
    repro_status: Optional[ReproductiveStage] = None
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `daily_calories_kcal` | `float` | ✅ | 由 L1 的 EnergyCalculator 计算得出 |
| `weight_kg` | `float` | ✅ | 影响食材总量规模 |
| `life_stage` | `LifeStage` | ✅ | 决定使用 `AAFCO_STANDARDS` 中哪个版本的约束 |

---

### `Ingredient`

食材定义（L1 输出后由数据层填充营养成分）。

```python
@dataclass
class Ingredient:
    id: str                          # 唯一 ID（与数据库主键对应）
    name: str                        # 显示名称
    slot: SlotType                   # 槽位类型
    nutrients: Dict[str, float]      # 营养成分字典 {nutrient_id: value/100g}
    calories_per_100g: float         # 热量（kcal/100g）
    tags: List[str] = []             # 风险标签，如 "risk_high_vit_a"
    category: str = None             # 食材品类（如 "poultry"/"fish"）
    is_supplement: bool = False      # 是否为补剂
```

> **注意**：`Ingredient` 中的 `nutrients` 字段在 `_solve_phase` 开始时会被 `nutrient_matrix` 覆盖，以 DataFrame 中的值为准。

---

### `L2Input`

L2 引擎的完整输入，由外层服务组装后传入。

```python
@dataclass
class L2Input:
    pet: PetProfile
    combination: RecipeCombination        # L1 生成的食材组合
    supplement_toolkit: List[Ingredient]  # 可用补剂列表（Phase 2 使用）
    nutrient_matrix: pd.DataFrame         # 原始营养成分矩阵（per 100g）
    nutrient_info: pd.DataFrame           # 营养素元信息（单位、名称等）
    nutrient_conversion_factor: Dict[int, float]   # 单位转换系数
    converted_nutrient_matrix: pd.DataFrame        # 已做单位转换的矩阵
```

**`nutrient_matrix` 格式要求：**

- 索引（`index`）：`ingredient_id`（字符串）
- 列（`columns`）：`NutrientID` 枚举成员
- 值：该食材每 100g 含有的营养素量（原始数据库单位）

**`converted_nutrient_matrix` 格式要求：**

- 与 `nutrient_matrix` 结构相同，但所有值已通过 `nutrient_conversion_factor` 转换为 AAFCO 标准单位
- 用于 `_parse_result` 中的结果分析（不参与求解器约束构建）

---

## 输出数据结构

### `OptimizationResult`

```python
@dataclass
class OptimizationResult:
    status: SolveStatus
    solve_time_seconds: float
    weights: Optional[List[OptimizedWeight]] = None
    total_weight_grams: Optional[float] = None
    nutrient_analysis: Optional[List[NutrientAnalysis]] = None
    objective_value: Optional[float] = None
    penalty_breakdown: Optional[Dict[str, float]] = None
    infeasibility_diagnostic: Optional[InfeasibilityDiagnostic] = None
    recipe_id: str = ""
    used_supplements: List[str] = []
```

| 字段 | 有值条件 | 说明 |
|------|----------|------|
| `weights` | OPTIMAL / FEASIBLE | 每种食材的最优重量列表 |
| `total_weight_grams` | OPTIMAL / FEASIBLE | 配方总重量（g） |
| `nutrient_analysis` | OPTIMAL / FEASIBLE | 所有营养素的达标分析 |
| `objective_value` | OPTIMAL / FEASIBLE | 目标函数值（越低越好） |
| `penalty_breakdown` | OPTIMAL / FEASIBLE | 各罚分分项（toxic/balance/supplement） |
| `infeasibility_diagnostic` | INFEASIBLE | 不可行原因诊断 |

---

### `OptimizedWeight`

```python
@dataclass
class OptimizedWeight:
    ingredient_id: str
    ingredient_name: str
    weight_grams: float       # 最优用量（g）
    is_supplement: bool = False
```

> 重量 < 0.1g 的食材会被过滤掉，不出现在结果中。

---

### `NutrientAnalysis`

```python
@dataclass
class NutrientAnalysis:
    nutrient_id: str
    nutrient_name: str
    value: float              # 实际值（per 1000 kcal ME）
    unit: str
    min_required: Optional[float] = None
    max_allowed: Optional[float] = None
    ideal_target: Optional[float] = None
    meets_min: bool = True    # 是否满足最低要求
    meets_max: bool = True    # 是否满足最高限制
    deviation_from_ideal: Optional[float] = None
```

---

### `InfeasibilityDiagnostic`

```python
@dataclass
class InfeasibilityDiagnostic:
    reason: InfeasibilityReason
    conflicting_nutrients: List[str]
    bottleneck_constraint: Optional[str] = None
    suggestion: Optional[str] = None
    details: Dict[str, Any] = {}
```

> **当前状态**：诊断系统为简化版，`reason` 固定返回 `UNKNOWN`，`_diagnose_infeasibility` 待完善。

---

## 配置结构

### `NutrientConstraint`

单个营养素的约束定义（用于 L2 内部逻辑，`AAFCO_STANDARDS` 使用字典格式而非此类）。

| 字段 | 说明 |
|------|------|
| `min` | 硬下限（LP 硬约束） |
| `max` | 通用硬上限 |
| `max_soft` | 软上限（罚分引导） |
| `max_hard` | 法定硬上限（绝对不可超） |
| `ideal` | 理想目标值（平衡罚分目标） |
| `safe_target` | ALARA 安全目标（分段罚分第一段） |
| `warning_target` | ALARA 警戒值（分段罚分第二段） |
| `priority` | 0=P0（毒性），1=P1（关键），2=P2（次要） |
| `penalty_type` | `"alara"` / `"balance"` / `None` |

---

### `SlotConstraint`

| 字段 | 说明 |
|------|------|
| `min_ratio` | 占总重的硬最小比例（LP 硬约束） |
| `max_ratio` | 占总重的硬最大比例（LP 硬约束） |
| `ideal_min` | 理想最小比例（软约束，罚分引导） |
| `ideal_max` | 理想最大比例（软约束，罚分引导） |

---

### `RiskTagConstraint`

| 字段 | 说明 |
|------|------|
| `tag` | 风险标签字符串（如 `"risk_high_iodine"`） |
| `max_ratio` | 带此标签的食材总重量占比上限（LP 硬约束） |
| `reason` | 说明 |

---

### `WeightConfig`（全局权重，位于 `l2_optimizer.py`）

```python
WEIGHT_CONFIG = {
    "toxic": 1e5,        # 毒性罚分权重（最高优先级）
    "balance": 50,       # 平衡罚分权重
    "supplement": 1e3,   # 补剂罚分权重
    "ca_p_ratio": 500,   # Ca:P 理想比率罚分权重
}
```

**调整指南：**

| 场景 | 建议调整 |
|------|----------|
| 配方总是缺钙 | 降低 `toxic`，提高 `balance` |
| 补剂使用过多 | 提高 `supplement`（如 5e3） |
| Ca:P 比率偏差大 | 提高 `ca_p_ratio`（如 1000） |
| 内脏类槽位占比不理想 | 提高槽位罚分权重（`_build_objective` 中的 `10 * slot_penalty`） |

---

## L2Optimizer（主入口）

### 构造函数

```python
L2Optimizer(debug: bool = False)
```

| 参数 | 说明 |
|------|------|
| `debug` | `True` 时在控制台打印两阶段进度信息 |

---

### `optimize(l2_input: L2Input) -> OptimizationResult`

**主入口方法**，执行两阶段求解。

```python
optimizer = L2Optimizer(debug=True)
result = optimizer.optimize(l2_input)
```

**Returns**: `OptimizationResult`

**内部执行顺序：**
1. `_solve_phase(use_supplements=False)` → Phase 1
2. 若 Phase 1 返回 `OPTIMAL`，直接返回
3. `_solve_phase(use_supplements=True)` → Phase 2
4. 返回 Phase 2 结果（无论成功与否）

---

### `_solve_phase(l2_input, use_supplements) -> OptimizationResult`

单阶段求解，内部流程：

```
1. 整合食材列表（基础食材 + 可选补剂）
2. 从 nutrient_matrix 填充 energy_per_100g
3. 创建 GLOP 求解器，超时 100 秒
4. _create_variables()        → 每个食材的重量变量 w_i ≥ 0
5. _add_hard_constraints()    → 热量、AAFCO、Ca:P、槽位、风险标签
6. _build_objective()         → 毒性 + 平衡 + Ca:P + 补剂 + 槽位软约束
7. solver.Minimize(objective)
8. _parse_result()            → 解析权重、计算营养分析
```

---

### `precalculate_conversion_factors(l2_input, life_stage) -> Dict[int, float]`

预计算营养素单位转换系数（如 mg → g），供调用方在构建 `L2Input` 时使用。

| 参数 | 说明 |
|------|------|
| `l2_input` | 完整输入（需含 `nutrient_matrix` 和 `nutrient_info`） |
| `life_stage` | 生命阶段（决定目标单位） |

**Returns**: `Dict[NutrientID, float]`，键为 `NutrientID`，值为单位转换系数。

> **注意**：此方法目前依赖 `UnitConverter` 工具类，需在 `app.common.utils` 中正确实现 `parse_unit_string` 和 `get_unit_factor`。

---

## AAFCO 营养标准

**文件**: `l2_aafco_config.py`  
**数据结构**: `AAFCO_STANDARDS: Dict[LifeStage, Dict[NutrientID | str, dict]]`  
**单位**: 所有值均为 **per 1000 kcal ME**（代谢能）

### 成犬（`LifeStage.DOG_ADULT`）关键约束

| 营养素 | 最小值 | 软上限 | 硬上限 | 单位 | 优先级 |
|--------|--------|--------|--------|------|--------|
| 蛋白质 | 45.0 | — | — | G | P1 |
| 脂肪 | 13.8 | — | — | G | P1 |
| 钙 | 1250 | 4500 | **6250** | MG | P0 |
| 磷 | 1000 | — | 4000 | MG | P0 |
| Ca:P 比率 | 1.0 | — | 2.0（理想 1.3） | — | P0 |
| 铁 | 10 | — | 500 | MG | P1 |
| 锌 | 20 | — | 250（理想 30） | MG | P2 |
| 铜 | 1.83 | — | 30（理想 5） | MG | P1 |
| 硒 | 80 | 120（ALARA） | 500 | UG | P0 |
| 碘 | 0.25 | 0.5（ALARA） | 2.75 | MG | P0 |
| 维生素 A | 1250 | 10000（ALARA） | 62500 | IU | P0 |
| 维生素 D | 125 | 200（ALARA） | **800** | IU | P0 |
| 维生素 E | 12.5 | — | 1000 | IU | P1 |
| 亚油酸（LA） | 2.8 | — | — | G | P1 |
| EPA+DHA 合计 | — | 0.11（推荐） | — | G | P2 |
| N6:N3 比率 | — | — | 30 | — | P2 |

### 幼犬（`LifeStage.DOG_PUPPY`）与成犬的主要差异

| 营养素 | 幼犬最小值 | 成犬最小值 | 说明 |
|--------|-----------|-----------|------|
| 蛋白质 | 56.3 G | 45.0 G | +25% |
| 脂肪 | 21.3 G | 13.8 G | +54% |
| 钙 | 3000 MG | 1250 MG | 骨骼发育需求 |
| 磷 | 2500 MG | 1000 MG | |
| EPA+DHA | 0.13 G（强制） | 0.11（推荐） | 神经发育 |

### 辅助函数

```python
get_constraint(life_stage: LifeStage, nutrient_id) -> dict
# 获取单个营养素的约束字典，不存在时返回 {}

get_all_p0_nutrients(life_stage: LifeStage) -> list
# 获取所有 P0 级别的营养素 ID 列表

validate_standards() -> bool
# 验证 AAFCO_STANDARDS 配置完整性，返回是否通过
```

---

## 槽位与风险约束

**文件**: `l2_slot_config.py`

### 槽位硬约束一览（`SLOT_CONSTRAINTS`）

| 槽位 | 硬最小比 | 硬最大比 | 理想范围 |
|------|----------|----------|----------|
| `MAIN_PROTEIN` | 30% | 90% | 40%-70% |
| `ORGAN_LIVER` | 0% | **6%** | 3%-5% |
| `ORGAN_SECRETING` | 0% | **7%** | 3%-5% |
| `ORGAN_MUSCULAR` | 0% | 20% | 5%-15% |
| `MINERAL_SHELLFISH` | 0% | 5% | 0%-3% |
| `VEGETABLE` | 0% | 15% | 5%-10% |
| `CARBOHYDRATE` | 0% | 25% | 0%-15% |
| `OMEGA3_LC` | 0% | 3% | 0.5%-2% |
| `OMEGA6_LA` | 0% | 3% | 0%-2% |
| `IODINE` | 0% | 1% | 0%-0.5% |
| `EGG` | 0% | 10% | 0%-10% |
| `SHELLFISH_PROTEIN` | 20% | 40% | 20%-30% |

### 子类特殊约束（`SUBGROUP_CONSTRAINTS`）

| 子类 | 硬最大比 | 原因 |
|------|----------|------|
| `organ_spleen` | 5% | 含铁量极高，过量导致软便 |
| `organ_brain` | 5% | 胆固醇含量高 |
| `organ_kidney` | 8% | 维生素 A 含量较高 |
| `supplement_calcium` | 2% | 优先从天然食材获取钙 |

### 风险标签约束（`RISK_TAG_CONSTRAINTS`）

| 标签 | 最大占比 | 原因 |
|------|----------|------|
| `risk_high_iodine` | 0.2% | 海带/海藻粉碘含量 1000-3000 mg/100g |
| `risk_high_vit_a` | 5% | 反刍动物肝脏维A极高 |
| `risk_laxative` | 5% | 脾脏/胰腺含消化酶过多导致腹泻 |
| `risk_high_oxalate` | 3% | 草酸钙结石风险 |
| `risk_expands` | 1% | 吸水膨胀 5-10 倍，肠梗阻风险 |
| `risk_high_purine` | 10% | 高尿酸风险 |
| `risk_goitrogen` | 5% | 致甲状腺肿，干扰碘吸收 |

### 辅助函数

```python
get_slot_constraint(slot: str) -> SlotConstraint | None
get_risk_constraint(tag: str) -> RiskTagConstraint | None
get_ingredients_with_slot(ingredients: list, slot: SlotType) -> list
get_ingredients_with_tag(ingredients: list, tag: str) -> list
check_mutual_exclusion(ingredients: list) -> list  # 返回互斥规则违规列表
calculate_slot_ratios(weights: dict, ingredients: list) -> dict
validate_slot_constraints(slot_ratios: dict) -> list
validate_constraints() -> bool  # 验证所有槽位约束的合理性
```

---

## 目标函数与罚分系统

目标函数：**最小化 Z**

```
Z = W_toxic × P_toxic
  + W_balance × P_balance
  + W_ca_p × P_ca_p
  + W_supplement × P_supplement  (仅 Phase 2)
  + 10 × P_slot
```

### 毒性罚分（ALARA，分段线性）

针对 Se、Vit D、Vit A、Iodine 四种营养素：

```
P_toxic = Σ [ w_safe × max(0, X - safe_target)
             + w_warning × max(0, X - warning_target) ]
```

| 营养素 | safe_target | warning_target | w_safe | w_warning | w_danger |
|--------|-------------|----------------|--------|-----------|----------|
| 硒 | 120 µg | 300 µg | 0 | 10 | 1000 |
| 维生素 D | 200 IU | 500 IU | 0 | 10 | 1000 |
| 维生素 A | 10000 IU | 30000 IU | 0 | 5 | 500 |
| 碘 | 0.5 mg | 1.5 mg | 0 | 50 | 2000 |

### 平衡罚分

针对 Zn、Mn、Cu，引导接近 `ideal` 值：

```
P_balance = Σ |X_i - ideal_i|  (绝对偏差，通过辅助变量线性化)
```

### Ca:P 理想比率罚分

```
P_ca_p = |Ca - 1.3 × P|  (绝对偏差)
```

### 补剂罚分（仅 Phase 2）

```
P_supplement = Σ coeff_i × w_i  (按补剂类型加权)
```

| 补剂类型关键字 | 系数 |
|--------------|------|
| kelp | 1.0 |
| zinc | 2.0 |
| vit_e | 3.0 |
| fish_oil | 4.0 |
| calcium | 5.0 |

### 槽位软约束罚分

```
P_slot = Σ [ max(0, ideal_min × W_total - W_slot)   # 低于理想下限
           + max(0, W_slot - ideal_max × W_total) ]  # 高于理想上限
```

---

## 两阶段求解策略

```python
# Phase 1: 仅使用 L1 提供的天然食材
result = _solve_phase(l2_input, use_supplements=False)
if result.status == OPTIMAL:
    return result  # ✅ 无需补剂

# Phase 2: 天然食材 + 补剂工具箱
result = _solve_phase(l2_input, use_supplements=True)
return result  # 返回结果（可能仍是 INFEASIBLE）
```

**Phase 2 补剂罚分机制** 确保补剂仅在必要时被使用——罚分权重 `1e3` 使求解器优先将补剂用量压为 0，只有在无法满足营养约束时才允许补剂加入。

---

## 约束层级总览

| 优先级 | 约束类型 | 实现方式 | 违反后果 |
|--------|----------|----------|----------|
| **P0** | 热量目标（±5%） | LP 硬约束 | INFEASIBLE |
| **P0** | AAFCO P0 营养素（Ca/P/Se/I/VitA/VitD） | LP 硬约束 | INFEASIBLE |
| **P0** | Ca:P 比率（0.8-2.5） | LP 硬约束 | INFEASIBLE |
| **P0** | 风险标签上限（高碘/高维A等） | LP 硬约束 | INFEASIBLE |
| **P1** | AAFCO P1 营养素（蛋白质/脂肪/铁等） | LP 硬约束 | INFEASIBLE |
| **P1** | 槽位硬上下限（min_ratio/max_ratio） | LP 硬约束 | INFEASIBLE |
| **P2** | AAFCO P2 营养素（氨基酸/B族维生素） | LP 硬约束 | INFEASIBLE |
| **软** | 毒性元素 ALARA（Se/VitA/VitD/I） | 罚分（W=1e5） | 目标函数升高 |
| **软** | 平衡元素接近 ideal（Zn/Mn/Cu） | 罚分（W=50） | 目标函数升高 |
| **软** | Ca:P 理想比率（1.3:1） | 罚分（W=500） | 目标函数升高 |
| **软** | 补剂用量最小化 | 罚分（W=1e3） | 目标函数升高 |
| **软** | 槽位理想范围（ideal_min/ideal_max） | 罚分（W=10） | 目标函数升高 |

---

## 使用示例

### 基础用法

```python
from l2_data_models import PetProfile, L2Input
from l2_optimizer import L2Optimizer
from app.common.enums import LifeStage

# 1. 创建宠物画像
pet = PetProfile(
    daily_calories_kcal=1200.0,   # 由 EnergyCalculator 计算
    weight_kg=20.0,
    life_stage=LifeStage.DOG_ADULT
)

# 2. 组装 L2Input（nutrient_matrix 等由数据层提供）
l2_input = L2Input(
    pet=pet,
    combination=l1_combination,      # L1 RecipeCombination
    supplement_toolkit=supplements,  # 补剂列表
    nutrient_matrix=matrix_df,
    nutrient_info=info_df,
    nutrient_conversion_factor=factors,
    converted_nutrient_matrix=converted_df
)

# 3. 运行优化
optimizer = L2Optimizer(debug=True)
result = optimizer.optimize(l2_input)

# 4. 处理结果
if result.status == SolveStatus.OPTIMAL:
    print(f"总重量: {result.total_weight_grams:.1f} g")
    for w in sorted(result.weights, key=lambda x: -x.weight_grams):
        flag = "💊" if w.is_supplement else "🥩"
        print(f"{flag} {w.ingredient_name}: {w.weight_grams:.1f}g")
    
    # 检查营养达标情况
    for a in result.nutrient_analysis:
        if not a.meets_min or not a.meets_max:
            print(f"⚠️ {a.nutrient_name}: {a.value:.1f} {a.unit} 不达标")
else:
    print(f"❌ {result.status.value}: {result.infeasibility_diagnostic.suggestion}")
```

---

### 验证约束配置

```python
from l2_aafco_config import validate_standards
from l2_slot_config import validate_constraints

validate_standards()    # 检查 AAFCO 标准完整性
validate_constraints()  # 检查槽位约束合理性（min < max，sum_min < 1.0 等）
```

---

## 营养学说明

### Ca:P 比率（v1.1 放宽）

AAFCO 推荐 Ca:P 比率为 1.0-2.0，理想值 1.3:1。但在**鲜食/生食配方**（Raw/Fresh Food）中：
- 纯肌肉肉的天然 Ca:P ≈ 0.05-0.15（磷远多于钙）
- 加入骨粉/蛋壳粉/碳酸钙后比例大幅提升
- 求解器需要足够的空间来"探索"加入钙源的可行域

因此 v1.1 将硬约束范围放宽至 **0.8-2.5**，同时通过罚分系统引导最终结果趋近 1.3:1。

### 维生素 D 上限（v1.1 修正）

AAFCO 2023 成犬法定上限为 **800 IU/1000kcal**（不是 750）。原值 750 与真实食材数据不匹配，会导致含三文鱼/沙丁鱼/肝脏的配方因 VitD 超标而被拒绝。NRC 安全上限为 3200 IU，ALARA 目标保持 200 IU。

### 分泌型内脏的风险

- **脾脏**（`organ_spleen`）：含铁量约 35-45 mg/100g，超过 5% 配方占比会显著增加软便风险
- **脑花**（`organ_brain`）：胆固醇约 2000 mg/100g，建议 ≤3%
- **海带粉**（`risk_high_iodine`）：碘含量 1000-3000 mg/100g，0.1g 即可接近日需求，需严格限制在 0.2% 以内

### 补剂选择优先级

从天然食材优先的角度，补剂选择顺序应为：
1. 海带粉（碘源）— 用量极少，成本低
2. 吡啶甲酸锌（锌补充）
3. 维生素 E 油
4. 鱼油（EPA/DHA）
5. 碳酸钙/骨粉（最后手段，优先从骨头/蛋壳获取）

---

## 修复记录 v1.1

| 编号 | 文件 | 问题 | 修复方案 |
|------|------|------|---------|
| #1 | `l2_optimizer.py` | `precalculate_conversion_factors` 中引用未定义变量 `ing`（第976行）和 `energy`（第1011行），调用即崩溃（`NameError`） | 删除孤立的 `kcal_val` 赋值行；注释掉 `get_base_factor` 调用并说明原因 |
| #2 | `l2_optimizer.py` | `_build_slot_penalty` 创建了偏差变量 `dev_min` / `dev_max` 但从未将其累加到 `penalty`，槽位软约束完全失效（两行 `penalty +=` 被注释掉） | 恢复 `penalty += dev_min` 和 `penalty += dev_max`，同时增加 `ingredient_id in self.vars` 的防御检查 |
| #3 | `l2_optimizer.py` | `_add_risk_tag_constraints` 调用被注释掉，高碘/高维A等风险约束全部未生效 | 取消注释，恢复调用 |
| #4 | `l2_aafco_config.py` | `validate_standards` 中对 `unit` 字段缺失的判断重复执行了两次（第914-918行），第一次判断无意义 | 删除重复判断，保留正确的一次 |
| #5 | `l2_aafco_config.py` | `PYRIDOXINE` 和 `FOLIC_ACID` 的 `nutrient_id` 字段错误写成 `NutrientID.NIACIN`，会导致分析报告中营养素 ID 错乱 | 修正为 `NutrientID.PYRIDOXINE` 和 `NutrientID.FOLIC_ACID` |
| #6 | `l2_aafco_config.py` | Vitamin D `max` 为 750 IU，低于 AAFCO 2023 法定上限 800 IU，导致含鱼/肝脏的正常配方被拒绝 | 修正为 800 IU，保持 ALARA 目标 200 IU 不变 |
| #7 | `l2_optimizer.py` | Ca:P 硬约束范围 1.0-2.0 对鲜食配方过于严格（肌肉肉天然 Ca:P ≈ 0.05-0.15），导致未加钙源前求解器直接 INFEASIBLE | 放宽硬约束至 0.8-2.5，AAFCO 推荐范围 1.0-2.0 通过罚分软约束引导 |
| #8 | `l2_aafco_config.py` | Calcium `max_hard` 写的是 4500 但注释写 6250——实际 AAFCO 2023 法定上限为 6250 mg/1000kcal | 修正 `max_hard=6250`，`max_soft=4500`（NRC 推荐软上限），注释与数值保持一致 |
| #9 | `l2_optimizer.py` | `_build_slot_penalty` 中 `weight_sum = sum(...)` 若 `ings` 内食材不在 `self.vars` 中会抛 `KeyError` | 加入 `if ing.ingredient_id in self.vars` 防御检查 |

