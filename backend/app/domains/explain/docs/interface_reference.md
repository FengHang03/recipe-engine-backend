# Recipe Explain 中间层接口参考文档

> **版本**：MVP Sprint 1  
> **对应 models.py schema**：1.0  
> **最后更新**：与当前代码库完全对齐

---

## 目录

1. [数据流总览](#1-数据流总览)
2. [models.py — 数据结构索引](#2-modelspy--数据结构索引)
3. [normalizer.py — Layer 1](#3-normalizerpy--layer-1)
4. [enrichment.py — Layer 2](#4-enrichmentpy--layer-2)
5. [derived_metrics.py — Layer 3](#5-derived_metricspy--layer-3)
6. [rule_engine/ — Layer 4](#6-rule_engine--layer-4)
7. [context_builder.py — Layer 5](#7-context_builderpy--layer-5)
8. [llm_service.py — Layer 6](#8-llm_servicepy--layer-6)
9. [router.py — API 端点](#9-routerpy--api-端点)
10. [预留接口索引](#10-预留接口索引)

---

## 1. 数据流总览

```
ExplainRecipeRequest
    │
    ▼  normalize()
NormalizedExplainInput
    │
    ▼  enrich()                          [async, DB]
EnrichedExplainInput
    │
    ▼  build()
DerivedMetrics
    │
    ▼  run_rule_engine()
RuleEngineResult
    │
    ▼  build_context()
RecipeExplanationContext
    │
    ▼  call_llm()                        [async, Anthropic API]
RecipeExplanationOutput
    │
    ▼  POST /recipes/explain response
```

---

## 2. models.py — 数据结构索引

### 输入结构（Section 1）

| 类名 | 用途 |
|---|---|
| `ExplainRecipeRequest` | API 入口，包含 `pet` + `recipe` |
| `PetProfileInput` | 前端传入的宠物档案，字段名保持原始（`weight_kg`，非 `body_weight_kg`） |
| `RecipeInput` | 食谱数据，含 `weights` + `nutrient_analysis` |
| `IngredientWeightInput` | 单食材条目，含 `pct_of_recipe`、`slot_type`（后端提供） |
| `NutrientAnalysisInput` | 单营养素分析条目，`nutrient_id` 为小写字符串 |

### Layer 1 输出（Section 2）

| 类名 | 用途 |
|---|---|
| `NormalizedExplainInput` | 清洗后的统一输入 |
| `NormalizedPetContext` | 统一字段名：`body_weight_kg`、`daily_calories_kcal` |
| `NormalizedRecipeContext` | `recipe_id` = `recipe_id` |
| `NormalizedIngredient` | 透传 `slot_type`，`pct_of_recipe`（已重命名） |

### Layer 2 输出（Section 3）

| 类名 | 用途 |
|---|---|
| `EnrichedExplainInput` | 包含 `normalized` + `enriched_ingredients` |
| `EnrichedIngredient` | 新增 `food_group`、`food_subgroup`、`max_g_per_kg_bw`、`role_tags`（规范化）、`risk_tags`（规范化）、`enrich_available` |

### Layer 3 输出（Section 4）

| 类名 | 用途 |
|---|---|
| `DerivedMetrics` | 所有派生指标汇总 |
| `IngredientMetric` | 含 `grams_per_kg_bw`、`food_subgroup`（透传）、coarse `food_group` |
| `CategoryTotal` | coarse category 聚合结果 |
| `StructureSnapshot` | 6 个布尔结构信号 |
| `IngredientSummary` | 预构建的 LLM 友好摘要（全量，裁剪在 LLMService） |
| `IngredientSummaryItem` | 含 `risk_tags`（预留，本版不使用） |

### Layer 4 输出（Section 5）

| 类名 | 用途 |
|---|---|
| `RuleEngineResult` | Rule Engine 全量输出 |
| `NutritionSummary` | `level1_findings` + `flagged_nutrients` + `ratio_findings` |
| `Level1Finding` | 4 个核心营养素状态（protein/fat/calcium/phosphorus） |
| `FlaggedNutrient` | 未达标或超标营养素，含 `severity`（high/medium） |
| `RatioFinding` | Ca:P 比值判断 |
| `FormulaReview` | `sanity_status` + `key_concerns`（规则确认的问题摘要） |
| `StrengthFlag` | 食谱优势信号 |
| `RiskFlag` | 用户级风险，含 `severity` + `priority`（int，越小越高） |
| `FeedingGuidanceFlag` | 喂养建议，含 `human_readable` |
| `IngredientAdjustmentIdea` | **预留，本版不填充** |

### Layer 5（Section 6）

| 类名 | 用途 |
|---|---|
| `RecipeExplanationContext` | 传给 LLMService 的完整 context（不裁剪） |
| `ExplanationPolicy` | LLM 行为参数，含 `max_strengths/risks/guidance_items` |

### Layer 6 输出（Section 7）

| 类名 | 用途 |
|---|---|
| `RecipeExplanationOutput` | API 最终返回，`schema_version: "1.0"` |
| `OverviewOutput` | `status` + `headline` + `summary` + `confidence` |
| `NutritionInterpretationOutput` | `overall_assessment` + `key_findings` |
| `KeyFindingOutput` | 单条营养发现，含 `title/status/importance/message` |
| `StrengthOutput` | 单条优势，含 `title/summary/why_it_matters` |
| `RiskOutput` | 单条风险，含 `severity/title/summary/why_it_matters/suggested_fix` |
| `FeedingGuidanceOutput` | 三组建议：`feeding_strategy/monitoring_points/adjustments_to_consider` |
| `GuidanceTextItem` | 单条建议文本 `{text: str}` |
| `PlainLanguageTakeaway` | `for_pet_parent`：给宠物主人的白话总结 |
| `IngredientAdjustmentIdeasOutput` | **预留，本版始终为空** |
| `MetaOutput` | `confidence` + `fallback_used` + `generated_from` |

---

## 3. normalizer.py — Layer 1

### `normalize(request: ExplainRecipeRequest) -> NormalizedExplainInput`

**作用**：清洗并统一 API 输入，不做任何业务判断。

| | 内容 |
|---|---|
| **输入** | `ExplainRecipeRequest` |
| **输出** | `NormalizedExplainInput` |
| **副作用** | 无 |

**字段转换：**

| 原字段 | 目标字段 | 规则 |
|---|---|---|
| `pet.weight_kg` | `body_weight_kg` | 重命名 + `float()` |
| `pet.daily_calories_kcal` | `daily_calories_kcal` | 重命名 + `float()` |
| `recipe.recipe_id` | `recipe_id` | 重命名 |
| `pet.species` | `species` | 统一小写 |
| `pet.life_stage` | `life_stage` | 统一大写，接受大/小/混合输入 |
| `nutrient_analysis[].nutrient_id` | `nutrient_id` | 统一小写 |
| `health_conditions` / `allergies` | 同名 | `None` → `[]` |

**降级行为**：任意字段清洗失败 → `logger.warning` → best-effort 保留所有可读字段，含 `size_class`（关键，影响小型犬规则）。

---

### 内部函数（不对外暴露）

| 函数 | 作用 |
|---|---|
| `_normalize_life_stage(raw)` | 处理大小写混合，未知值 pass-through + warning |
| `_normalize_species(raw)` | 转小写 |
| `_normalize_nutrient_id(raw)` | strip + 转小写 |
| `_normalize_pet_context(pet)` | 构建 `NormalizedPetContext` |
| `_normalize_recipe_context(recipe)` | 构建 `NormalizedRecipeContext` |
| `_normalize_ingredients(recipe)` | 构建 `List[NormalizedIngredient]`，单条失败 skip |
| `_normalize_nutrient_analysis(recipe)` | 构建 `List[NutrientAnalysisInput]`，单条失败 skip |

---

## 4. enrichment.py — Layer 2

### `enrich(normalized: NormalizedExplainInput, db: Any) -> EnrichedExplainInput`

**作用**：按 `ingredient_id` 批量查询 Cloud SQL，为每个食材补充元信息，并将 DB 原始 tag 规范化为 explain 层标准 tag。

| | 内容 |
|---|---|
| **输入** | `NormalizedExplainInput`, `db`（SQLAlchemy AsyncSession） |
| **输出** | `EnrichedExplainInput` |
| **副作用** | 两次 DB 查询（`ingredients` + `ingredient_tags`） |

**DB 查询：**

```sql
-- ingredients 表
SELECT ingredient_id, food_group, food_subgroup,
       max_g_per_kg_bw, max_pct_kcal
FROM   ingredients
WHERE  ingredient_id = ANY(:ids)

-- ingredient_tags 表（tag_type: "role" | "risk" | "note"）
SELECT ingredient_id, tag_type, tag
FROM   ingredient_tags
WHERE  ingredient_id = ANY(:ids)
```

**Tag 规范化（`_ROLE_TAG_MAP`）：**

| DB 原始 tag | 规范化后 |
|---|---|
| `role_omega3_ala`, `role_omega3_lc` | `omega3_source` |
| `role_calcium` | `calcium_source` |
| `role_iron` | `iron_source` |
| `role_zinc` | `zinc_source` |
| `role_iodine` | `iodine_source` |
| `role_vita` | `vitamin_a_source` |
| `role_vitd` | `vitamin_d_source` |
| `role_vit_b1` | `vitamin_b1_source` |
| `role_vit_b12` | `vitamin_b12_source` |
| `role_choline` | `choline_source` |
| `role_fiber_source` | `fiber_source` |

**`_RISK_TAG_MAP`：** DB 原始值（如 `risk_high_copper`）直接透传，不做映射。

**降级行为：**
- `ingredients` 表查询失败 → 所有食材 `enrich_available=False`，流程继续
- `ingredient_tags` 表查询失败 → tag 字段为空，基础数据保留
- 单个 `ingredient_id` 不存在 → 该食材 `enrich_available=False`，其他不影响

---

## 5. derived_metrics.py — Layer 3

### `build(enriched: EnrichedExplainInput) -> DerivedMetrics`

**作用**：纯计算，无 DB，无 LLM，无副作用。从 `EnrichedExplainInput` 派生所有可解释指标。

| | 内容 |
|---|---|
| **输入** | `EnrichedExplainInput` |
| **输出** | `DerivedMetrics` |
| **副作用** | 无 |

**计算内容：**

| 字段 | 计算方式 |
|---|---|
| `grams_per_kg_bw` | `weight_grams / body_weight_kg`（防零除，默认 1.0） |
| `pct_of_recipe` | 透传自后端（已计算） |
| `category_totals` | 按 **coarse category** 聚合，使用 `_COARSE_CATEGORY_MAP` |
| `ca_p_ratio` | `calcium.value / phosphorus.value`，任一 None 或 P=0 返回 None |
| `structure_snapshot` | 6 个布尔字段，见下表 |
| `supplement_count` | `is_supplement == True` 的数量 |
| `ingredient_summary` | 预构建，全量，按 `pct_of_recipe` 降序排列 |

**`_COARSE_CATEGORY_MAP`（DB FoodGroup → coarse）：**

| DB FoodGroup | coarse |
|---|---|
| `PROTEIN_MEAT/FISH/EGG/SHELLFISH`, `MINERAL_SHELLFISH` | `protein` |
| `ORGAN` | `organ` |
| `CARB_GRAIN/TUBER/LEGUME/OTHER` | `carb` |
| `PLANT_ANTIOXIDANT` | `vegetable`（蓝莓/浆果类经名称正则覆盖为 `fruit`） |
| `FAT_OIL` | `fat_oil` |
| `FIBER` | `fiber` |
| `SUPPLEMENT` | `supplement` |
| `TREAT` | `treat` |
| `DAIRY` | `dairy` |
| 未知 | `other` |

**`PLANT_ANTIOXIDANT` 细分**：`_FRUIT_BY_NAME` 正则匹配（blueberry/raspberry/cranberry/cherry 等），命中则 coarse → `fruit`；beet/eggplant/red cabbage 保持 `vegetable`。

**`structure_snapshot` 判断依据：**

| 字段 | 主判断 | 兜底 |
|---|---|---|
| `has_main_protein` | `slot_type == "Main Protein Slot"` | coarse == `protein` 且 `pct_of_recipe >= 10` |
| `has_calcium_source` | `role_tags` 含 `calcium_source` | — |
| `has_omega3_support` | `role_tags` 含 `omega3_source` | — |
| `has_carbohydrate_source` | coarse == `carb` | — |
| `has_vegetable` | coarse == `vegetable` | — |
| `has_liver` | coarse == `organ` | — |

---

## 6. rule_engine/ — Layer 4

### `run_rule_engine(enriched, derived) -> RuleEngineResult`（engine.py 主入口）

**作用**：串联所有规则子模块，生成完整 `RuleEngineResult`，是事实的唯一来源，LLM 不得推翻其结论。

| | 内容 |
|---|---|
| **输入** | `EnrichedExplainInput`, `DerivedMetrics` |
| **输出** | `RuleEngineResult` |
| **副作用** | 无 |

**执行顺序：**
1. `nutrition_rules.run()` → NutritionSummary + 营养 Strength/Risk flags
2. `structure_rules.run()` → 结构 Strength/Risk flags
3. `realism_rules.run()` → ingredient_amount Risk flags
4. `realism_rules.check_g_per_kg_bw()` → g/kg BW Risk flags
5. `guidance_rules.run()` → FeedingGuidanceFlags
6. `_build_formula_review()` → FormulaReview

---

### nutrition_rules.run(nutrient_analysis, derived) → Tuple[NutritionSummary, List[StrengthFlag], List[RiskFlag]]

**Level1 营养素（4 个）：** protein / fat / calcium / phosphorus

| 阈值 | status | 同时生成 |
|---|---|---|
| `value >= min_required * 1.2` | `strong` | StrengthFlag（protein only） |
| `value >= min_required` | `adequate` | — |
| `value < min_required` | `low` | FlaggedNutrient + RiskFlag（`low_{nutrient_id}`） |
| `value > max_allowed`（若有） | `high` | FlaggedNutrient |

**FlaggedNutrient severity**：偏离 min_required > 30% → `high`，否则 `medium`。

**Ca:P ratio 阈值：**

| 范围 | status | severity |
|---|---|---|
| `< 0.8` | `abnormal` | `high` |
| `[0.8, 1.0)` | `borderline` | `medium` |
| `[1.0, 2.0]` | `normal` | — → StrengthFlag `balanced_ca_p_ratio` |
| `(2.0, 2.5]` | `borderline` | `medium` |
| `> 2.5` | `abnormal` | `high` |

**Deficiency RiskFlag codes（`nutrient_deficiency` type）：**

| code | priority |
|---|---|
| `low_calcium` | 1 |
| `low_phosphorus` | 2 |
| `low_protein` | 2 |
| `low_fat` | 3 |

---

### structure_rules.run(snapshot, derived) → Tuple[List[StrengthFlag], List[RiskFlag]]

**Strength Flags：**

| 触发条件 | code | priority |
|---|---|---|
| `has_main_protein` | `clear_main_protein_present` | high |
| `has_calcium_source` | `clear_calcium_source_present` | high |
| `supplement_count <= 2` | `limited_supplement_dependency` | medium |

**Risk Flags：**

| 触发条件 | code | severity | priority |
|---|---|---|---|
| `not has_calcium_source` | `missing_calcium_source` | high | 1 |
| `not has_omega3_support` | `missing_omega3_support` | medium | 3 |
| `supplement_count >= 5` | `high_supplement_dependency` | medium | 4 |

---

### realism_rules.run(ingredient_metrics, pet_context) → List[RiskFlag]

| 触发条件 | code | severity | priority |
|---|---|---|---|
| coarse==`fruit` + `DOG_PUPPY` + size in `[toy,small]` + pct > 10% | `high_fruit_for_small_puppy` | medium | 3 |
| coarse==`fruit` + pct > 15%（上条未触发时） | `high_fruit_proportion` | medium | 4 |
| `food_subgroup == "organ_liver"` + pct > 5% | `high_liver_proportion` | medium | 3 |

两条 fruit 规则互斥：`high_fruit_for_small_puppy` 触发后自动压制 `high_fruit_proportion`。

### realism_rules.check_g_per_kg_bw(ingredient_metrics, enrich_map) → List[RiskFlag]

| 触发条件 | code | severity | priority |
|---|---|---|---|
| `grams_per_kg_bw > max_g_per_kg_bw`（来自 enrich） | `ingredient_exceeds_g_per_kg_bw_limit` | medium | 3 |

---

### guidance_rules.run(pet_context, risk_flags, flagged_nutrient_ids) → List[FeedingGuidanceFlag]

| 触发条件 | code | type | priority |
|---|---|---|---|
| `DOG_PUPPY` + size in `[toy,small]` | `split_into_3_meals_for_small_puppy` | feeding_strategy | high |
| 存在 `high_fruit_*` / `high_liver_proportion` / `ingredient_exceeds_g_per_kg_bw_limit` | `watch_stool_quality` | monitoring | medium |
| `DOG_PUPPY` 或 `DOG_SENIOR` | `monitor_body_weight_and_condition` | monitoring | medium |
| 存在 `missing_calcium_source` 或 calcium flagged | `increase_calcium_support` | adjustment | high |
| 存在 `ca_p_ratio_below/above_target` | `rebalance_calcium_phosphorus` | adjustment | high |
| 存在 `missing_omega3_support` | `add_omega3_support` | adjustment | medium |
| 存在 `high_fruit_*` | `reduce_fruit_proportion` | adjustment | medium |

`human_readable` 由 `CODE_TO_READABLE` dict 填充，所有 7 条 code 均有对应文本。

---

## 7. context_builder.py — Layer 5

### `build_context(normalized, derived, rule_result, policy=None) -> RecipeExplanationContext`

**作用**：纯组装，将 Layer 1–4 的输出组合成 `RecipeExplanationContext`，不做任何裁剪或判断。

| | 内容 |
|---|---|
| **输入** | `NormalizedExplainInput`, `DerivedMetrics`, `RuleEngineResult`, `ExplanationPolicy?` |
| **输出** | `RecipeExplanationContext` |
| **副作用** | 无 |

所有字段直接透传。`ingredient_summary` 为全量（裁剪在 `build_user_prompt()`）。`policy` 默认为 `ExplanationPolicy()`。

---

## 8. llm_service.py — Layer 6

### `call_llm(context: RecipeExplanationContext) -> RecipeExplanationOutput`

**作用**：构建 prompt，调用 Anthropic API，解析结构化 JSON 响应。任何异常自动 fallback。

| | 内容 |
|---|---|
| **输入** | `RecipeExplanationContext` |
| **输出** | `RecipeExplanationOutput` |
| **副作用** | Anthropic API 调用（`claude-sonnet-4-20250514`，max_tokens=1500） |

**失败行为**：任意异常 → `logger.error` → 调用 `generate_fallback_output()`，返回 200 + `meta.fallback_used=True`。

---

### `_build_user_prompt(context)` — 两层裁剪

**Pass 1 — 全局 exclude（`_EXCLUDE_FIELDS`）：**

```
nutrient_id, evidence_code, reason_code, ratio_id,
recommended_action_code, enrich_available, food_subgroup,
activity_level, sterilization_status, reproductive_stage,
health_conditions, allergies
```

**Pass 2 — 按模块 trim：**

| 模块 | 裁剪规则 |
|---|---|
| `level1_findings` | 全量（最多 4 条） |
| `flagged_nutrients` | severity 降序，最多 3 条 |
| `ratio_findings` | 全量 |
| `ingredients` | 最多 6 条，优先顺序：pct>15% → priority categories（organ/fruit/fat_oil） → pct 降序补足 |
| `category_totals` | 只保留：`organ/fruit/fat_oil/supplement/other` |
| `structure_snapshot` | 全量（6 bool） |
| `strength_flags` | priority 升序，最多 3 条 |
| `risk_flags` | severity 优先，再按 priority，最多 4 条 |
| `feeding_guidance_flags` | priority 升序，最多 4 条 |

---

### `generate_fallback_output(context) -> RecipeExplanationOutput`

**作用**：LLM 失败时基于 Rule Engine 事实生成模板化输出，无 LLM 依赖。

| 字段 | 来源 |
|---|---|
| `overview.status` | `formula_review.sanity_status` |
| `overview.confidence` | `"low"` |
| `nutrition_interpretation.overall_assessment` | `key_concerns` 拼接 |
| `nutrition_interpretation.key_findings` | `_build_fallback_key_findings()`：flagged → ratio → level1，最多 3 条 |
| `strengths[].title` | `_STRENGTH_CODE_TO_TITLE` 映射 |
| `risks[].title` | `_RISK_CODE_TO_TITLE` 映射 |
| `risks[].summary` | `_KEY_CONCERN_MAP` 映射 |
| `risks` 排序 | severity 优先，再按 priority |
| `feeding_guidance` | 按 flag type 分组：`feeding_strategy/monitoring/adjustment` |
| `meta.confidence` | `"low"` |
| `meta.fallback_used` | `True` |

---

### `_build_fallback_key_findings(context, max_findings=3) -> List[KeyFindingOutput]`

来源优先级：
1. `flagged_nutrients`（severity 降序）
2. `ratio_findings`（非 normal）
3. `level1_findings`（status 为 strong/adequate）

---

## 9. router.py — API 端点

### `POST /recipes/explain`

| | 内容 |
|---|---|
| **Request Body** | `ExplainRecipeRequest` |
| **Response** | `RecipeExplanationOutput` |
| **Content-Type** | `application/json` |

**错误响应：**

| HTTP 状态码 | 原因 |
|---|---|
| `422` | 请求体字段校验失败（FastAPI 自动） |
| `500` | Pipeline 内部错误（Rule Engine / DB） |
| `200` + `meta.fallback_used=true` | LLM 调用失败，返回 fallback 结果 |

**执行步骤：**

```python
normalized = normalize(request)
enriched   = await enrich(normalized, db)
derived    = build_derived_metrics(enriched)
rule_result= run_rule_engine(enriched, derived)
context    = build_context(normalized, derived, rule_result)
output     = await call_llm(context)
return output
```

**注意**：`get_db` 为占位符，需替换为项目实际的 async DB session factory。

---

## 10. 预留接口索引

以下接口已在代码中预留，本版不填充：

| 接口 | 位置 | 激活条件 |
|---|---|---|
| `IngredientAdjustmentIdea` 填充 | `RuleEngineResult.ingredient_adjustment_ideas` | 后端 gap_analysis 完成 |
| `RecipeExplanationContext.improvement_suggestions` | 字段待加 | 同上 |
| `RecipeExplanationOutput.ingredient_adjustment_ideas` | 始终为空 `IngredientAdjustmentIdeasOutput()` | 同上 |
| `pct_of_recipe > max_pct_kcal` 规则 | `realism_rules.py` 注释占位 | `percentage` 字段统一后 |
| `IngredientSummaryItem.risk_tags` | 字段存在，值透传 | 下个 sprint 展示层使用 |
| `ExplanationPolicy.language` | 固定 `"en"` | i18n 需求 |
| `health_conditions` 适配规则 | `NormalizedPetContext` 字段保留 | 兽医规则库完成后 |
| `level2_triggered_findings` | `NutritionSummary` 注释占位 | 下下个 sprint |
| `static_candidates.py` | 数据已定义 | 下个 sprint `IngredientAdjustmentIdea` 激活时 |
