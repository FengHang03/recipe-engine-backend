# L1 Recipe Generator — 接口文档

**模块版本**: v1.1（含 Bug 修复）  
**涉及文件**: `l1_config.py` · `l1_slot_scheduler.py` · `l1_recipe_generator.py`

---

## 目录

1. [枚举类型](#枚举类型)
2. [配置模型](#配置模型)
   - [IngredientFilter](#ingredientfilter)
   - [ExclusionRule](#exclusionrule)
   - [SlotConfig](#slotconfig)
   - [DependencyConfig](#dependencyconfig)
   - [L1Config](#l1config)
3. [SlotScheduler](#slotscheduler)
4. [CombinationGenerator](#combinationgenerator)
5. [L1RecipeGenerator（主入口）](#l1recipegenerator主入口)
6. [数据类型：RecipeCombination / Ingredient](#数据类型)
7. [槽位一览表](#槽位一览表)
8. [依赖规则逻辑说明](#依赖规则逻辑说明)
9. [互斥规则一览](#互斥规则一览)
10. [使用示例](#使用示例)
11. [修复记录](#修复记录-v11)

---

## 枚举类型

### `FoodGroup`

食材大类，用于槽位筛选器的 `allowed_groups` 字段。

| 值 | 含义 |
|----|------|
| `PROTEIN_MEAT` | 肉类蛋白 |
| `PROTEIN_FISH` | 鱼类蛋白 |
| `PROTEIN_EGG` | 蛋类 |
| `PROTEIN_SHELLFISH` | 蛋白质贝类 |
| `MINERAL_SHELLFISH` | 矿物质贝类（牡蛎、贻贝等） |
| `ORGAN` | 内脏（统一大类，通过 FoodSubgroup 细分） |
| `CARB_GRAIN` | 谷物碳水 |
| `CARB_TUBER` | 薯类碳水 |
| `CARB_LEGUME` | 豆类碳水 |
| `CARB_OTHER` | 其他碳水 |
| `PLANT_ANTIOXIDANT` | 抗氧化植物（蔬菜） |
| `FAT_OIL` | 脂肪/油脂（非核心食材） |
| `FIBER` | 纤维类 |
| `SUPPLEMENT` | 补充剂（非核心食材） |
| `TREAT` | 零食 |
| `DAIRY` | 乳制品 |

---

### `FoodSubgroup`

食材子类，用于槽位筛选器的 `allowed_subgroups` 字段及互斥规则的 `target_subgroups`。

**内脏子类（3-subgroup 方案）**

| 值 | 含义 | L2 用量约束 |
|----|------|------------|
| `organ_liver` | 肝脏（鸡肝/牛肝/猪肝） | Max 5% kcal（维A风险） |
| `organ_kidney` | 肾脏 | Combined Max 5% |
| `organ_spleen` | 脾脏 | ≤ 3%（铁风险） |
| `organ_brain` | 脑花 | ≤ 3%（胆固醇风险） |
| `organ_secreting` | 其他分泌型（胰腺、睾丸） | Combined Max 5% |
| `heart` | 心脏 | 无限制，计入肉类蛋白 |
| `gizzard` | 胗（鸡胗/鸭胗） | 无限制，计入肉类蛋白 |
| `organ_muscular` | 其他肌肉型（舌、肺、肚） | 无限制，计入肉类蛋白 |

**其他子类**

| 值 | 含义 |
|----|------|
| `meat_lean` | 瘦肉（触发强制碳水规则） |
| `meat_moderate` | 中脂肉 |
| `meat_fat` | 高脂肉 |
| `fish_lean` | 瘦鱼（触发强制碳水规则） |
| `fish_oily` | 油鱼（含 omega3，触发跳过鱼油规则） |
| `plant_orange/green/blue/white` | 蔬菜颜色分类（多样性控制） |
| `supplement_calcium` | 钙补充剂 |
| `supplement_iodine` | 碘补充剂 |
| `supplement_omega3_lc` | Omega-3 LC 补充剂 |
| `oil_omega3_lc` | Omega-3 油脂 |
| `oil_omega6_la` | Omega-6 油脂 |
| `fiber_plant` | 植物纤维 |
| `supplement_fiber` | 纤维补充剂 |

---

## 配置模型

### `IngredientFilter`

定义槽位允许放入哪些食材（所有条件为 AND 关系）。

```python
class IngredientFilter(BaseModel):
    allowed_groups: List[FoodGroup] = []
    allowed_subgroups: List[FoodSubgroup] = []
    required_tags: List[str] = []      # 食材必须包含这些标签（全部满足）
    excluded_tags: List[str] = []      # 食材不能包含这些标签（任一排除）
    diversity_tags: List[str] = []     # 优先考虑的多样性标签（仅用于提示）
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `allowed_groups` | `List[FoodGroup]` | 允许的食材大类，为空则不限制 |
| `allowed_subgroups` | `List[FoodSubgroup]` | 允许的食材子类，为空则不限制 |
| `required_tags` | `List[str]` | 食材必须**全部包含**的标签 |
| `excluded_tags` | `List[str]` | 食材**不能包含任何一个**的标签 |
| `diversity_tags` | `List[str]` | 多样性提示标签（不强制过滤） |

---

### `ExclusionRule`

互斥规则，限制某类食材在一个组合中出现的最大数量。

```python
class ExclusionRule(BaseModel):
    rule_id: str
    target_subgroups: List[FoodSubgroup] = []
    target_groups: List[FoodGroup] = []
    target_tags: List[str] = []
    max_count: int = 1
    max_total_weight_g: float | None = None
    reason: str = ""
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `rule_id` | `str` | 规则唯一标识 |
| `target_subgroups` | `List[FoodSubgroup]` | 目标子类（匹配任意一个即计入） |
| `target_groups` | `List[FoodGroup]` | 目标大类 |
| `target_tags` | `List[str]` | 目标标签（含任意一个即计入） |
| `max_count` | `int` | 匹配食材的最大数量，超过则剪枝 |
| `max_total_weight_g` | `float \| None` | 重量限制（L1 阶段不使用，由 L2 执行） |
| `reason` | `str` | 规则说明（文档用途） |

> **注意**：`target_subgroups` 与 `target_tags` 同时配置时，食材匹配任一条件即计入 `matched_count`（OR 关系），而非 AND。

---

### `SlotConfig`

定义单个槽位的静态属性。

```python
class SlotConfig(BaseModel):
    name: str
    description: str = ""
    is_mandatory_default: bool = True
    initial_state: str = "optional"     # "mandatory" | "optional" | "disabled"
    filters: IngredientFilter
    max_items: int = 1
    min_item: int = 0
    apply_diversity: bool = False
    min_weight_g: float | None = None
    max_weight_g: float | None = None
    is_core_ingredient: bool = True
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `initial_state` | `str` | 初始槽位状态：`"mandatory"` / `"optional"` / `"disabled"` |
| `max_items` | `int` | 此槽位最多选几种食材 |
| `min_item` | `int` | 此槽位最少选几种食材（`mandatory` 状态下会被覆盖为 1） |
| `apply_diversity` | `bool` | 是否应用多样性约束（排除已用 diversity_cluster） |
| `is_core_ingredient` | `bool` | 是否计入核心食材数量（`FAT_OIL`/`SUPPLEMENT` 为 `False`） |
| `max_weight_g` | `float \| None` | 槽位级别重量上限（传递给 L2，L1 不强制） |

---

### `DependencyConfig`

定义槽位之间的动态依赖策略开关。所有字段默认为 `True`。

| 字段 | 默认值 | 触发效果 |
|------|--------|---------|
| `skip_omega3_lc_if_oily_fish` | `True` | 主蛋白含 `role_omega3_lc` 标签 → 禁用 `omega3_lc` 槽 |
| `skip_omega6_la_if_fatty_meat` | `True` | 主蛋白含 `role_omega6_la` 标签 → 禁用 `omega6_la` 槽 |
| `force_carb_if_lean_protein` | `True` | 主蛋白为 `meat_lean`/`fish_lean` → 强制 `carbohydrate` 必选 |
| `allow_no_carb_if_fatty_protein` | `True` | 主蛋白为 `meat_moderate`/`meat_fat` → `carbohydrate` 恢复可选 |
| `skip_fiber_if_carb_has_fiber` | `True` | 已选食材含 `role_fiber_source` → 禁用 `fiber` 槽 |
| `force_fiber_if_no_carb` | `True` | 无碳水且无纤维源 → 强制 `fiber` 必选 |
| `skip_iodine_if_high_iodine_ingredient` | `True` | 已选食材含 `risk_high_iodine` → 禁用 `iodine` 槽 |
| `force_main_protein_if_shellfish` | `True` | 已选贝类 → 强制选择主蛋白（肉/鱼） |
| `choose_optional_ingredients` | `True` | 核心食材未满 9 种 → `optional_ingredients` 保持可选；已满 → 禁用 |

---

### `L1Config`

L1 层总配置，整合以上所有配置。

```python
class L1Config(BaseModel):
    policies: DependencyConfig          # 依赖规则开关
    exclusion_rules: List[ExclusionRule]  # 互斥规则列表
    slots: Dict[str, SlotConfig]        # 槽位配置字典
```

**创建默认配置：**
```python
from l1_config import L1Config, get_default_config

config = L1Config()          # 等价于
config = get_default_config()
```

---

## SlotScheduler

`l1_slot_scheduler.py`

管理槽位状态，根据已选食材动态启用/禁用槽位。

### 构造函数

```python
SlotScheduler(config: L1Config, ingredients_df: pd.DataFrame)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `config` | `L1Config` | L1 配置对象 |
| `ingredients_df` | `pd.DataFrame` | 食材数据表（从数据库加载） |

### 公开方法

#### `reset()`

重置调度器到初始状态（清空已选食材，恢复槽位初始状态）。  
在每次 `generate_combinations()` 开始时自动调用。

---

#### `set_slot_state(slot_name, state, reason="")`

手动设置槽位状态。

| 参数 | 类型 | 合法值 |
|------|------|--------|
| `slot_name` | `str` | 槽位名称（见槽位一览表） |
| `state` | `str` | `"mandatory"` / `"optional"` / `"disabled"` |
| `reason` | `str` | 日志说明（可选） |

---

#### `is_slot_mandatory(slot_name) -> bool`

返回指定槽位当前是否为 `"mandatory"` 状态。

---

#### `get_active_slots() -> List[str]`

返回当前所有非 `"disabled"` 槽位的名称列表。

---

#### `select_ingredients_for_slot(slot_name, ingredients)`

为指定槽位设置已选食材，并自动触发 `apply_dependencies()` 重新评估所有依赖规则。

| 参数 | 类型 | 说明 |
|------|------|------|
| `slot_name` | `str` | 槽位名称 |
| `ingredients` | `List[Ingredient]` | 已选食材列表 |

---

#### `apply_dependencies()`

根据 `selected_ingredients` 的当前状态，评估并更新所有槽位的动态状态。  
由 `select_ingredients_for_slot()` 自动调用，一般不需要手动调用。

**执行顺序：**
1. 物种一致性约束（`_apply_species_constraints`）
2. Omega3 LC 逻辑
3. Omega6 LA 逻辑
4. 碳水逻辑
5. 纤维逻辑（已修复条件反转 Bug）
6. 碘槽逻辑
7. 可选食材槽逻辑

---

#### `get_slot_candidates(slot_name, limit=None, exclude_used_diversity=True) -> List[Ingredient]`

获取指定槽位的候选食材列表。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `slot_name` | `str` | — | 槽位名称 |
| `limit` | `int \| None` | `None` | 最多返回 N 个食材 |
| `exclude_used_diversity` | `bool` | `True` | 是否排除已用 `diversity_cluster` |

**Returns**: `List[Ingredient]`，已通过 `IngredientFilter` 过滤。

---

## CombinationGenerator

`l1_recipe_generator.py`

递归回溯生成所有合法食材组合。通常由 `L1RecipeGenerator` 内部管理，不需要直接使用。

### 构造函数

```python
CombinationGenerator(
    scheduler: SlotScheduler,
    config: L1Config,
    max_core_ingredients: int = 9
)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `scheduler` | `SlotScheduler` | 已初始化的槽位调度器 |
| `config` | `L1Config` | L1 配置 |
| `max_core_ingredients` | `int` | 核心食材数量上限（不含 FAT_OIL/SUPPLEMENT） |

### 主要方法

#### `generate_combinations(max_combinations=1000, enable_pruning=True) -> List[RecipeCombination]`

生成所有合法组合，计算评分，按 `(completeness, diversity, -risk)` 降序排列后返回。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_combinations` | `int` | `1000` | 最大组合数 |
| `enable_pruning` | `bool` | `True` | 是否在回溯时提前检查互斥规则（建议保持 True） |

**Returns**: `List[RecipeCombination]`，已排序。

---

### 评分方法

#### `_calculate_diversity_score(combo) -> float`

多样性评分（0-1），基于组合内不同 `diversity_cluster` 的数量，归一化分母为 10。

#### `_calculate_risk_score(combo) -> float`

风险评分（0-1，**越低越好**），基于组合内 `risk_*` 标签的种类数量，归一化分母为 5。

#### `_calculate_completeness_score(combo) -> float`

完整性评分（0-1），基于 `组合实际启用槽位数 / 当前激活槽位总数`。  
> **v1.1 修复**：原实现以全部配置槽位数为分母，现改为以实际激活槽位数为分母，评分更准确。

---

## L1RecipeGenerator（主入口）

`l1_recipe_generator.py`

L1 层对外暴露的主入口类。

### 构造函数

```python
L1RecipeGenerator(
    ingredients_df: pd.DataFrame,
    config: Optional[L1Config] = None,
    max_core_ingredients: int = 9
)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ingredients_df` | `pd.DataFrame` | — | 食材数据（从数据库加载） |
| `config` | `L1Config \| None` | `None` | 自定义配置，`None` 则使用默认配置 |
| `max_core_ingredients` | `int` | `9` | 核心食材数量上限 |

**`ingredients_df` 必须包含的列：**

| 列名 | 类型 | 说明 |
|------|------|------|
| `ingredient_id` | `str` | 食材唯一 ID |
| `description` | `str` | 食材完整名称 |
| `short_name` | `str` | 食材简称 |
| `food_group` | `str` | 食材大类（`FoodGroup` 的值） |
| `food_subgroup` | `str` | 食材子类（`FoodSubgroup` 的值） |
| `tags` | `List[str]` | 标签列表 |
| `diversity_cluster` | `str \| None` | 多样性聚类标识 |
| `energy_per_100g` | `float \| None` | 每 100g 能量（kcal） |
| `max_g_per_kg_bw` | `float \| None` | 每 kg 体重最大用量（g） |
| `max_pct_kcal` | `float \| None` | 最大能量占比 |

---

### `generate(max_combinations=500, dog_profile=None) -> List[RecipeCombination]`

**主入口方法**，生成候选食材组合列表。

```python
combinations = l1_generator.generate(
    max_combinations=500,
    dog_profile=None
)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_combinations` | `int` | `500` | 最大生成组合数 |
| `dog_profile` | `Dict \| None` | `None` | 狗的健康信息（见下方结构） |

**`dog_profile` 结构：**

```python
dog_profile = {
    "name": str,                  # 狗的名字（日志用）
    "weight_kg": float,           # 体重（kg）
    "age_years": int,             # 年龄（岁）
    "conditions": List[str],      # 健康状况，支持：
                                  #   "hyperlipidemia" → 排除 risk_cholesterol 食材
                                  #   "kidney_disease" → 建议 L2 控制蛋白质/磷
    "allergies": List[str],       # 过敏原，例如 ["chicken", "beef"]
                                  # 会自动转换为 allergen_{name} 标签排除
    "preferences": Dict           # 预留，当前未使用
}
```

> **v1.1 修复**：`dog_profile` 的过敏原/健康限制现在对 `self.config` **完全无副作用**，每次调用均操作深拷贝副本，多次调用结果互相独立。

**Returns**: `List[RecipeCombination]`，已按 `(completeness_score DESC, diversity_score DESC, risk_score ASC)` 排序。

**Raises**:
- 无主动异常，内部错误通过 `logger.error` 记录。

---

### `export_combinations_summary(combinations, top_n=10) -> pd.DataFrame`

导出组合摘要，用于调试和查看。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `combinations` | `List[RecipeCombination]` | — | 组合列表 |
| `top_n` | `int` | `10` | 只返回前 N 个组合 |

**Returns**: `pd.DataFrame`，列包含 `recipe_id`、`n_ingredients`、`active_slots`、`diversity_score`、`risk_score`、`completeness_score`、以及每个槽位的 `slot_{name}` 列。

---

## 数据类型

### `Ingredient`

食材对象（由 `SlotScheduler._df_to_ingredients()` 从 DataFrame 转换）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `ingredient_id` | `str` | 唯一 ID |
| `description` | `str` | 完整名称 |
| `short_name` | `str` | 简称 |
| `food_group` | `str` | 食材大类 |
| `food_subgroup` | `str` | 食材子类 |
| `tags` | `List[str]` | 标签列表 |
| `diversity_cluster` | `str \| None` | 多样性聚类 |
| `diversity_tags` | `List[str]` | 多样性标签 |
| `energy_per_100g` | `float \| None` | 每 100g 能量 |
| `max_g_per_kg_bw` | `float \| None` | 每 kg 体重最大用量 |
| `max_pct_kcal` | `float \| None` | 最大能量占比 |

**常用方法：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `has_tag(tag)` | `bool` | 是否含有指定标签 |
| `has_any_tag(tags)` | `bool` | 是否含有任意一个标签 |
| `get_protein_diversity_tag()` | `str \| None` | 获取 `div_protein_*` 标签 |

---

### `RecipeCombination`

一个完整的食材组合对象，由 `CombinationGenerator` 创建。

| 字段 | 类型 | 说明 |
|------|------|------|
| `recipe_id` | `str` | 唯一 ID，格式 `combo_XXXX` |
| `ingredients` | `Dict[str, List[Ingredient]]` | 按槽位分组的食材字典 |
| `diversity_score` | `float` | 多样性评分（0-1，越高越好） |
| `risk_score` | `float` | 风险评分（0-1，越低越好） |
| `completeness_score` | `float` | 完整性评分（0-1，越高越好） |
| `active_slots` | `List[str]` | 实际有食材的槽位名称列表 |

**常用方法：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `get_all_ingredients()` | `List[Ingredient]` | 获取所有食材（扁平化列表） |
| `get_ingredient_ids()` | `List[str]` | 获取所有食材 ID（传递给 L2） |
| `calculate_ingredient_stats()` | `None` | 计算食材统计信息（由评分时自动调用） |

---

## 槽位一览表

| 槽位名 | 显示名 | 初始状态 | 最大数量 | 核心食材 | 说明 |
|--------|--------|----------|----------|----------|------|
| `main_protein` | Main Protein | mandatory | 1 | ✅ | 主蛋白（肉/鱼），排除 `risk_high_copper` |
| `egg` | Egg | mandatory | 1 | ✅ | 鸡蛋（必选） |
| `shellfish_protein` | Shellfish Protein | optional | 1 | ✅ | 蛋白贝类（默认关闭） |
| `calcium` | Calcium | mandatory | 1 | ✅ | 钙源，需含 `role_calcium_source` 标签 |
| `mineral_shellfish` | Mineral Shellfish | mandatory | 1 | ✅ | 矿物质贝类（牡蛎等） |
| `organ_liver` | Organ Liver | mandatory | 1 | ✅ | 肝脏，Max weight 50g |
| `organ_secreting` | Organ Secreting | mandatory | 1 | ✅ | 分泌型内脏，Max weight 100g |
| `organ_muscular` | Organ Muscular | optional | 2 | ✅ | 肌肉型内脏（可选，可多选） |
| `vegetable` | Vegetable | mandatory | 2 | ✅ | 蔬菜，启用多样性约束 |
| `omega3_lc` | Omega3 LC | mandatory | 1 | ❌ | 鱼油/Omega3 补充剂，含 `role_omega3_lc` |
| `omega6_la` | Omega6 LA | mandatory | 1 | ❌ | 植物油，含 `role_omega6_la` |
| `carbohydrate` | Carbohydrate | optional | 1 | ✅ | 碳水（条件必选） |
| `iodine` | Iodine | mandatory | 1 | ❌ | 碘补充剂（含高碘食材时跳过） |
| `fiber` | Fiber | optional | 1 | ❌ | 纤维（无碳水时条件必选） |
| `optional_ingredients` | Optional Ingredients | optional | 1 | ❌ | 零食/乳制品（核心食材未满时可选） |

---

## 依赖规则逻辑说明

以下规则在每次 `select_ingredients_for_slot("main_protein", ...)` 后自动触发：

```
1. 物种一致性
   主蛋白含 div_protein_X 标签
   → organ_liver 排除含相同标签的肝脏（避免 Beef + Beef Liver 同源）

2. Omega3 逻辑
   主蛋白含 role_omega3_lc
   → omega3_lc 槽 disabled（油鱼已提供，不再补充鱼油）

3. Omega6 逻辑
   主蛋白含 role_omega6_la
   → omega6_la 槽 disabled（高脂肉已提供，不再补充植物油）

4. 碳水逻辑
   主蛋白 subgroup == meat_lean 或 fish_lean
   → carbohydrate 槽 mandatory（瘦肉能量不足，需要碳水补充）
   否则
   → carbohydrate 恢复 optional

5. 纤维逻辑（已修复 v1.1）
   任意已选食材含 role_fiber_source
   → fiber 槽 disabled（已有纤维来源）
   否则，无碳水 AND force_fiber_if_no_carb=True
   → fiber 槽 mandatory（无碳水则必须显式补充纤维）
   否则
   → fiber 恢复默认状态

6. 碘逻辑
   任意已选食材含 risk_high_iodine
   → iodine 槽 disabled（已有高碘食材，不再额外补碘）

7. 可选食材逻辑
   核心食材数 < 9 → optional_ingredients optional
   核心食材数 >= 9 → optional_ingredients disabled
```

---

## 互斥规则一览

| rule_id | 目标子类 | max_count | 说明 |
|---------|----------|-----------|------|
| `organ_total_limit` | liver + kidney + spleen + brain + organ_secreting + organ_muscular | 3 | 内脏总种类不超过 3 |
| `liver_limit` | liver | 1 | 肝脏只能选 1 种（维生素 A 风险） |

---

## 使用示例

### 基础使用

```python
from data_loader import IngredientDataLoader
from l1_recipe_generator import L1RecipeGenerator

# 1. 加载食材数据
loader = IngredientDataLoader(connection_string="postgresql://...")
ingredients_df = loader.load_ingredients_for_l1()

# 2. 创建生成器（使用默认配置）
generator = L1RecipeGenerator(ingredients_df)

# 3. 生成组合
combinations = generator.generate(max_combinations=500)

# 4. 查看摘要
summary = generator.export_combinations_summary(combinations, top_n=10)
print(summary)

# 5. 传递给 L2
for combo in combinations[:10]:
    ingredient_ids = combo.get_ingredient_ids()
    # l2_optimizer.optimize(ingredient_ids=ingredient_ids, ...)
```

---

### 带健康档案的生成

```python
dog_profile = {
    "name": "Max",
    "weight_kg": 10.0,
    "age_years": 5,
    "conditions": ["hyperlipidemia"],  # 排除高胆固醇食材
    "allergies": ["chicken"],          # 排除含 allergen_chicken 标签的食材
    "preferences": {}
}

# 每次调用完全独立，不会污染默认配置
combinations_sick = generator.generate(max_combinations=300, dog_profile=dog_profile)
combinations_normal = generator.generate(max_combinations=500)  # 不受上次影响
```

---

### 自定义配置

```python
from l1_config import L1Config

config = L1Config()

# 强制开启碳水槽
config.slots["carbohydrate"].initial_state = "mandatory"
config.slots["carbohydrate"].is_mandatory_default = True

# 蔬菜最多 3 种
config.slots["vegetable"].max_items = 3

# 关闭 omega6 自动跳过
config.policies.skip_omega6_la_if_fatty_meat = False

generator = L1RecipeGenerator(ingredients_df, config=config)
combinations = generator.generate(max_combinations=200)
```

---

### 导出 CSV

```python
from export_combinations import export_combinations_to_csv, export_combinations_to_excel

# 详细格式：每个槽位单独一列
export_combinations_to_csv(combinations, "output.csv", format_style="detailed")

# 紧凑格式：所有食材合并一列
export_combinations_to_csv(combinations, "output_compact.csv", format_style="compact")

# Excel 格式：含 Overview / Details / Statistics 三个 sheet
export_combinations_to_excel(combinations, "output.xlsx")
```

---

## 修复记录 v1.1

| 编号 | 文件 | 问题 | 修复方案 |
|------|------|------|---------|
| #1 | `l1_slot_scheduler.py` | 纤维逻辑条件反转：`force_fiber_if_no_carb` 嵌套在 `skip_fiber_if_carb_has_fiber` 的 `else` 分支，导致两个 policy 同时为 True 时强制纤维规则永远不触发 | 两个 policy 独立判断，互不嵌套 |
| #2 | `l1_slot_scheduler.py` | 拼写错误 `"diasble"` 导致槽位状态为非法值 | 修正为 `"disabled"` |
| #3 | `l1_slot_scheduler.py` | `is_slot_mandatory()` 引用了未定义的 `self.mandatory_slots`，调用即崩溃 | 改为从 `self.slot_states` 读取 |
| #4 | `l1_slot_scheduler.py` | `apply_dependencies()` 末尾重复调用 `_apply_species_constraints()`（函数开头已调用） | 删除末尾冗余调用 |
| #5 | `l1_config.py` | `organ_total_limit` 规则 `max_count=3` 但 `reason` 写"最多2种"，文档误导 | 统一 `reason` 为"总共最多3种" |
| #6 | `l1_recipe_generator.py` | `itertools.combinations` 在循环体内每次 import | 移至文件顶部 |
| #7 | `l1_recipe_generator.py` | `_apply_dog_profile()` 直接修改共享 `self.config`，导致过敏原/健康限制在下次调用时残留 | `generate()` 中对 config 做 `deepcopy`，隔离副作用，生成完成后恢复原始引用 |
| #8 | `l1_slot_scheduler.py` | `get_slot_candidates()` 中无效 `df.copy()` 立刻被覆盖，且 `_apply_filters` 内部已有 copy，导致双重拷贝 | 删除无效 copy |
| #9 | `l1_recipe_generator.py` | 核心食材满时直接 `return`，跳过后续所有非核心槽位（omega/iodine/supplement），导致这些成分丢失 | 核心食材满时只跳过当前核心槽，通过继续递归 `next_slots` 确保非核心槽得到处理 |
| #10 | `l1_recipe_generator.py` | `completeness_score` 以全部配置槽位数为分母（含 disabled），导致评分系统性偏低且不准确 | 改为以当前激活槽位数为分母 |
| #11 | `l1_config.py` | 未使用的 `from sqlalchemy.sql.dml import ReturningInsert` | 删除 |
| #12 | `l1_recipe_generator.py` | 未使用的 `from numpy import core` | 删除 |
