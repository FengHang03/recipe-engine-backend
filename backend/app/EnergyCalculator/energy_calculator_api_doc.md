# EnergyCalculator 接口文档

**模块**: `energy_calculator.py`  
**版本**: `EnergyCalculator-v0.3`  
**适用对象**: 犬、猫

---

## 目录

1. [枚举类型](#枚举类型)
2. [数据类](#数据类)
3. [EnergyCalculator 方法](#energycalculator-方法)
   - [calculate_resting_energy_requirement](#calculate_resting_energy_requirement)
   - [get_life_stage_factor](#get_life_stage_factor)
   - [get_activity_factor](#get_activity_factor)
   - [get_lactation_factor](#get_lactation_factor)
   - [get_breed_size_factor](#get_breed_size_factor)
   - [calculate_daily_energy_requirement](#calculate_daily_energy_requirement)
4. [计算公式说明](#计算公式说明)
5. [使用示例](#使用示例)
6. [更新日志](#更新日志)

---

## 枚举类型

### `Species`

| 值 | 含义 |
|----|------|
| `Species.DOG` | 犬 |
| `Species.CAT` | 猫 |

---

### `LifeStage`

| 值 | 含义 |
|----|------|
| `LifeStage.DOG_PUPPY` | 幼犬（0-11 月） |
| `LifeStage.DOG_ADULT` | 成年犬（12-84 月） |
| `LifeStage.DOG_SENIOR` | 老年犬（> 84 月） |
| `LifeStage.CAT_KITTEN` | 幼猫（0-12 月） |
| `LifeStage.CAT_ADULT` | 成年猫（13-84 月） |
| `LifeStage.CAT_SENIOR` | 老年猫（> 84 月） |

> **注意**：老年判断阈值默认为 84 月（7 岁），可通过 `senior_month` 参数自定义。

---

### `ActivityLevel`

| 值 | 描述 | 活动系数 |
|----|------|----------|
| `ActivityLevel.SEDENTARY` | 极少运动 | 1.4 |
| `ActivityLevel.LOW` | 低活动量 | 1.6 |
| `ActivityLevel.MODERATE` | 中等活动量 | 1.8 |
| `ActivityLevel.HIGH` | 高活动量 | 2.0 |
| `ActivityLevel.EXTREME` | 极高活动量 | 2.2 |

---

### `SterilizationStatus`

| 值 | 含义 |
|----|------|
| `SterilizationStatus.INTACT` | 未绝育 |
| `SterilizationStatus.NEUTERED` | 已绝育（活动系数降低 0.2，最低不低于 1.0） |

---

### `ReproductiveStage`

| 值 | 含义 |
|----|------|
| `ReproductiveStage.NONE` | 正常（非怀孕/哺乳） |
| `ReproductiveStage.PREGNANT` | 怀孕中 |
| `ReproductiveStage.LACTATING` | 哺乳中 |

---

## 数据类

### `EnergyCalculationResult`

`calculate_daily_energy_requirement` 的返回值。

| 字段 | 类型 | 说明 |
|------|------|------|
| `resting_energy_kcal` | `float` | 静息能量需求（kcal/天），精确到 0.1 |
| `daily_energy_kcal` | `float` | 每日能量需求（kcal/天），精确到 0.1 |
| `life_stage` | `str` | 生命阶段字符串（LifeStage 枚举的 `.value`） |
| `model_version` | `str` | 计算模型版本号，如 `"EnergyCalculator-v0.3"` |
| `calculation_breakdown` | `Dict[str, float]` | 各步骤中间值，详见下表 |
| `warnings` | `list[str]` | 警告信息列表，无警告时为空列表 |

#### `calculation_breakdown` 字段说明

| 键 | 出现条件 | 含义 |
|----|----------|------|
| `rer` | 始终 | 静息能量需求（kcal） |
| `life_stage_factor` | 始终 | 生命阶段系数 |
| `base_der` | 非手动指定 | 基础每日能量需求（kcal） |
| `activity_factor_base` | 正常状态 | 原始活动系数 |
| `neutered_adjustment` | 已绝育 | 绝育调整量（固定 -0.2） |
| `senior_adjustment` | 老年 | 老年调整量（固定 -0.2） |
| `activity_factor_final` | 正常状态 | 最终活动系数 |
| `breed_factor` | 正常状态 | 品种体型系数 |
| `der_final` | 正常状态 | 最终每日能量需求（kcal） |
| `pregnancy_multiplier` | 怀孕 | 怀孕系数（固定 1.8） |
| `pregnancy_addition` | 怀孕 | 体重相关增量（kcal） |
| `der_after_pregnancy` | 怀孕 | 调整后每日能量需求（kcal） |
| `lactation_factor` | 哺乳 | 哺乳周系数 |
| `lactation_week` | 哺乳 | 哺乳周数 |
| `nursing_count` | 哺乳 | 哺乳幼崽数量 |
| `puppy_energy` | 哺乳 | 幼崽能量分量（kcal） |
| `der_after_lactation` | 哺乳 | 调整后每日能量需求（kcal） |
| `manual_override` | 手动指定 | 手动指定的能量值（kcal） |

---

## EnergyCalculator 方法

### `calculate_resting_energy_requirement`

```python
@staticmethod
def calculate_resting_energy_requirement(weight_kg: float) -> float
```

计算静息能量需求（RER）。

**公式**：`RER = 70 × weight_kg^0.75`

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `weight_kg` | `float` | ✅ | 体重（公斤），必须大于 0 |

#### 返回值

`float` — RER（千卡/天）

#### 异常

| 异常 | 触发条件 |
|------|----------|
| `ValueError` | `weight_kg <= 0` |

> 体重超过 50kg 时会记录 `WARNING` 日志，但不抛出异常。

---

### `get_life_stage_factor`

```python
@staticmethod
def get_life_stage_factor(
    species: Species,
    age_months: int,
    senior_month: int = 84,
) -> tuple[float, LifeStage]
```

根据物种和月龄返回生命阶段系数与阶段枚举值。

#### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `species` | `Species` | ✅ | — | 物种 |
| `age_months` | `int` | ✅ | — | 年龄（月） |
| `senior_month` | `int` | ❌ | `84` | 老年起始月龄 |

#### 返回值

`tuple[float, LifeStage]` — `(系数, 生命阶段枚举值)`

#### 月龄区间与系数对照

| 物种 | 月龄区间 | LifeStage | 系数 |
|------|----------|-----------|------|
| 犬 | [0, 4) | `DOG_PUPPY` | 3.0 |
| 犬 | [4, 12) | `DOG_PUPPY` | 3.0 |
| 犬 | [12, senior_month] | `DOG_ADULT` | 1.0 |
| 犬 | > senior_month | `DOG_SENIOR` | 1.0 |
| 猫 | [0, 12] | `CAT_KITTEN` | 2.5 |
| 猫 | (12, senior_month] | `CAT_ADULT` | 1.0 |
| 猫 | > senior_month | `CAT_SENIOR` | 1.0 |

---

### `get_activity_factor`

```python
@staticmethod
def get_activity_factor(
    age_months: int,
    activity_level: ActivityLevel,
    is_young: bool,
) -> float
```

获取活动系数。幼年动物的系数范围会被压缩，避免与生命阶段系数重复叠加。

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `age_months` | `int` | ✅ | 年龄（月） |
| `activity_level` | `ActivityLevel` | ✅ | 活动水平枚举值 |
| `is_young` | `bool` | ✅ | 是否为幼年动物 |

#### 返回值

`float` — 活动系数

> 幼年动物：`factor = 1.0 + (base_factor - 1.8) × 0.25`，范围约为 0.9-1.1。  
> 成年动物：直接返回 `ACTIVITY_FACTORS[activity_level]`。

---

### `get_lactation_factor`

```python
@staticmethod
def get_lactation_factor(lactation_week: int) -> float
```

获取哺乳周数对应的系数。

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `lactation_week` | `int` | ✅ | 哺乳周数（1-8） |

#### 返回值

`float` — 哺乳周系数

#### 哺乳周系数表

| 周数 | 系数 | 说明 |
|------|------|------|
| 1 | 0.75 | 哺乳初期 |
| 2 | 0.95 | 逐渐增加 |
| 3 | 1.10 | 上升期 |
| 4 | 1.20 | 产奶高峰 |
| 5 | 1.20 | 产奶高峰持平 |
| 6 | 1.10 | 开始回落 |
| 7 | 0.90 | 减少期 |
| 8 | 0.75 | 逐渐断奶 |

#### 异常

| 异常 | 触发条件 |
|------|----------|
| `ValueError` | `lactation_week < 1` 或 `lactation_week > 8` |

---

### `get_breed_size_factor`

```python
@staticmethod
def get_breed_size_factor(
    weight_kg: float,
    breed: Optional[str] = None,
) -> float
```

根据品种标识或体重返回体型系数。

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `weight_kg` | `float` | ✅ | 体重（公斤） |
| `breed` | `Optional[str]` | ❌ | 品种体型标识，优先于体重推断 |

#### `breed` 合法值

| 值 | 体重范围 | 系数 |
|----|----------|------|
| `'toy'` | < 5 kg | 0.95 |
| `'small'` | 5-10 kg | 1.00 |
| `'medium'` | 10-25 kg | 1.00 |
| `'large'` | 25-45 kg | 1.05 |
| `'giant'` | > 45 kg | 1.10 |

> 若 `breed` 为 `None` 或不在合法值列表中，则按 `weight_kg` 自动推断体型。

#### 返回值

`float` — 体型系数

---

### `calculate_daily_energy_requirement`

```python
@classmethod
def calculate_daily_energy_requirement(
    cls,
    weight_kg: float,
    species: Species,
    age_months: int,
    activity_level: ActivityLevel,
    sterilization_status: SterilizationStatus,
    reproductive_stage: ReproductiveStage,
    breed: Optional[str] = None,
    lactation_week: Optional[int] = 4,
    nursing_count: Optional[int] = 1,
    senior_month: Optional[int] = 84,
    energy_requirement: Optional[float] = None,
) -> EnergyCalculationResult
```

计算宠物每日能量需求（DER），为本模块的核心接口。

#### 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `weight_kg` | `float` | ✅ | — | 体重（公斤），必须大于 0 |
| `species` | `Species` | ✅ | — | 物种 |
| `age_months` | `int` | ✅ | — | 年龄（月），不能为负数 |
| `activity_level` | `ActivityLevel` | ✅ | — | 活动水平 |
| `sterilization_status` | `SterilizationStatus` | ✅ | — | 绝育状态 |
| `reproductive_stage` | `ReproductiveStage` | ✅ | — | 生理状态（正常/怀孕/哺乳） |
| `breed` | `Optional[str]` | ❌ | `None` | 品种体型标识 |
| `lactation_week` | `Optional[int]` | ❌ | `4` | 哺乳周数（1-8），仅哺乳状态时生效 |
| `nursing_count` | `Optional[int]` | ❌ | `1` | 哺乳幼崽数量，仅哺乳状态时生效 |
| `senior_month` | `Optional[int]` | ❌ | `84` | 老年起始月龄 |
| `energy_requirement` | `Optional[float]` | ❌ | `None` | 手动指定能量需求（kcal），传入后跳过所有系数计算 |

#### 返回值

`EnergyCalculationResult` — 详见[数据类](#数据类)章节。

#### 异常

| 异常 | 触发条件 |
|------|----------|
| `ValueError` | `weight_kg <= 0`、`age_months < 0`、`energy_requirement <= 0` |
| `RuntimeError` | 计算过程中发生非预期错误 |

#### 自动警告（写入 `warnings` 字段）

| 触发条件 | 警告内容 |
|----------|----------|
| `weight_kg < 0.5` | 体重过小，结果可能不准确 |
| `weight_kg > 100` | 体重过大，请确认是否正确 |
| `age_months > senior_month` | 老年宠物，能量需求已降低 |
| 幼年动物处于怀孕/哺乳状态 | 自动重置为正常状态并警告 |
| 传入 `energy_requirement` | 提示使用手动指定值 |

#### 计算流程

```
RER = 70 × weight_kg^0.75

基础 DER = life_stage_factor × RER

怀孕：DER = 基础DER × 1.8 + 26 × weight_kg

哺乳：DER = 145 × weight_kg^0.75
           + puppy_energy × lactation_week_factor

正常：DER = 基础DER × activity_factor × breed_factor
```

---

## 使用示例

### 示例 1：成年犬（正常状态）

```python
result = EnergyCalculator.calculate_daily_energy_requirement(
    weight_kg=15.0,
    species=Species.DOG,
    age_months=36,
    activity_level=ActivityLevel.MODERATE,
    sterilization_status=SterilizationStatus.NEUTERED,
    reproductive_stage=ReproductiveStage.NONE,
    breed='medium',
)

print(result.daily_energy_kcal)     # 每日能量需求（kcal）
print(result.resting_energy_kcal)   # 静息能量需求（kcal）
print(result.life_stage)            # "dog_adult"
print(result.warnings)              # []
```

### 示例 2：哺乳期母犬

```python
result = EnergyCalculator.calculate_daily_energy_requirement(
    weight_kg=20.0,
    species=Species.DOG,
    age_months=24,
    activity_level=ActivityLevel.LOW,
    sterilization_status=SterilizationStatus.INTACT,
    reproductive_stage=ReproductiveStage.LACTATING,
    lactation_week=3,
    nursing_count=5,
)

print(result.daily_energy_kcal)
print(result.calculation_breakdown['lactation_factor'])   # 1.1
print(result.calculation_breakdown['nursing_count'])      # 5
```

### 示例 3：手动指定能量需求

```python
result = EnergyCalculator.calculate_daily_energy_requirement(
    weight_kg=10.0,
    species=Species.CAT,
    age_months=48,
    activity_level=ActivityLevel.MODERATE,
    sterilization_status=SterilizationStatus.NEUTERED,
    reproductive_stage=ReproductiveStage.NONE,
    energy_requirement=280.0,   # 直接使用此值，跳过系数计算
)

print(result.daily_energy_kcal)     # 280.0
print(result.warnings)              # ['使用手动指定的能量需求']
```

---

## 更新日志

### v0.3（当前版本）

- **[Fix #1]** 补全哺乳周数系数第 5-8 周，避免 `.get()` 静默返回错误默认值
- **[Fix #2]** 月龄边界常量重命名（加 `_EXCLUSIVE` / `_INCLUSIVE` 后缀），消除歧义
- **[Fix #3]** 注释明确老年判断为 `> senior_month`（84 月整归属成年）
- **[Fix #4]** 修正 `calculate_resting_energy_requirement` 中 log 信息错别字
- **[Fix #5]** 合并幼年动物生理状态 warning，去除重复消息
- **[Fix #6]** 修正 `energy_requirement` 参数类型注解为 `Optional[float]`
- **[Fix #7]** 哺乳期计算中魔法数字 `96` 提取为 `LACTATION_BASE_4_PUPPIES` 常量
- **[Fix #8]** 补充注释说明 `PUPPY_EARLY_FACTOR` 与 `PUPPY_LATE_FACTOR` 暂时相同
- **[Fix #9]** `get_life_stage_factor` 增加 `senior_month` 参数，与主函数参数同步

### v0.2

- 初始发布版本
