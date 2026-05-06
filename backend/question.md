# 中间层输出
## RecipeExplanationContext
    {
        "pet_context": {},
        "recipe_context": {},
        "nutrition_summary": {},
        "ingredient_summary": {},
        "formula_review": {},
        "strength_flags": [],
        "risk_flags": [],
        "feeding_guidance_flags": [],
        "explanation_policy": {}
    }

### pet_context
        {
            "species": "dog",
            "breed": "Mini Poodle",
            "life_stage": "DOG_PUPPY",
            "age_months": 8,
            "body_weight_kg": 5.0,
            "size_class": "small",
            "activity_level": "moderate",
            "daily_calories_kcal": 380.0,
            "sterilization_status": "intact",
            "reproductive_stage": "none",
            "health_conditions": [],
            "allergies": []
        }

        先只保证前 5 个字段
        字段	    	必填	来源	是否给 LLM	说明
        species	        ✅	Normalizer	✅	dog / cat
        life_stage	    ✅	Normalizer	✅	DOG_PUPPY / ADULT / SENIOR
        age_months	    ⚠️	Normalizer	    ✅	用于解释语境
        body_weight_kg	✅	Normalizer	✅	用于 grams/kg
        size_class	    ⚠️	Normalizer	✅	small / medium / large
        daily_calories_kcal	✅	Normalizer	✅	用于解释能量背景
        activity_level	❌	Normalizer	❌	中间层可用，LLM可不需要
        sterilization_status	❌	Normalizer	❌	MVP 可不传
        health_conditions	❌	Normalizer	❌	未来扩展
        allergies	    ❌	Normalizer	❌	未来扩展

### recipe_context
        {
            "recipe_id": "abc-123",
            "rank": 1,
            "total_weight_grams": 420.0,
            "total_ingredients_count": 7
            "used_supplements": ["Eggshell Powder"],
            "supplement_count": 1,
            "non_supplement_count": 6
        }

        LLM 需要: recipe_id + total_weight_grams + used_supplement(可选)
        字段	必填	来源	是否给 LLM	说明
        recipe_id	✅	Normalizer	✅	= recipe_id
        rank	⚠️	Normalizer	❌	UI用，不重要
        total_weight_grams	✅	Normalizer	✅	解释结构
        total_ingredients_count	✅	Derived	❌	规则用
        supplement_count	✅	Derived	❌	结构风险
        non_supplement_count	✅	Derived	❌	结构判断
        used_supplements	⚠️	Normalizer	❌	可选
        objective_value	❌	可选	❌	LP内部指标

### nutrition_summary 
        核心模块    
        {
            "level1_findings": [
                {
                "nutrient_id": "protein",
                "nutrient_name": "Protein",
                "category": "macro",
                "status": "strong",
                "priority": "high",
                "value": 55.0,
                "unit": "g",
                "min_required": 45.0,
                "max_allowed": null,
                "ideal_target": null,
                "evidence_code": "above_minimum"
                }
            ],
            "flagged_nutrients": [
                {
                "nutrient_id": "calcium",
                "display_name": "Calcium",
                "category": "mineral_balance",
                "status": "low",
                "severity": "high",
                "reason_code": "below_minimum",
                "value": 0.8,
                "unit": "g",
                "min_required": 1.0,
                "max_allowed": null
                }
            ],
            "ratio_findings": [
                {
                "ratio_id": "ca_p_ratio",
                "display_name": "Ca:P Ratio",
                "status": "borderline",
                "severity": "high",
                "value": 0.9,
                "min_target": 1.0,
                "max_target": 2.0,
                "reason_code": "below_ratio_min"
                }
            ],
            "level2_triggered_findings": [
                {
                "nutrient_id": "iodine",
                "display_name": "Iodine",
                "status": "high",
                "severity": "medium",
                "reason_code": "risk_tag_or_near_upper_bound"
                }
            ]
        }

#### level1_findings
            字段	必填	来源	给LLM	说明
            nutrient_id	✅	Rule	❌	内部用
            display_name	✅	Rule	✅	Protein / Calcium
            status	✅	Rule	✅	strong / adequate / low / high
            priority	✅	Rule	✅	P0 / P1 / P2
            value	⚠️	Rule	✅	一级营养素建议给
            min_required	⚠️	Rule	✅	
            max_allowed	❌	Rule	❌	
            reason_code	⚠️	Rule	❌	fallback用

#### flagged_nutrients
            字段	必填	来源	给LLM
            nutrient_id	✅	Rule	❌
            issue_type	✅	Rule	❌
            severity	✅	Rule	✅
            priority	✅	Rule	✅
            value	✅	Rule	✅
            min_required	⚠️	Rule	✅
            max_allowed	❌	Rule	❌
            reason_code	⚠️	Rule	❌

#### ratio_findings
            字段	必填	来源	给LLM
            ratio_name	✅	Derived	❌
            value	✅	Derived	✅
            target_range	⚠️	Rule	❌
            status	✅	Rule	✅
            priority	✅	Rule	✅
        
#### level2_triggered_findings
        MVP 先不做
    
### ingredient_summary
        核心模块
        {
            "ingredients": [
                {
                "ingredient_name": "Blueberry",
                "weight_grams": 40.0,
                "percentage_of_recipe": 9.5,
                "grams_per_kg_bw": 8.0,
                "food_group": "fruit_blue",
                "slot_type": "Optional Ingredients Slot",
                "role_tags": [],
                "risk_tags": [],
                "note_tags": []
                }
            ],
            "category_totals": [
                {
                "category": "organ_liver",
                "total_grams": 20.0,
                "pct_of_recipe": 4.8
                },
                {
                "category": "fruit",
                "total_grams": 40.0,
                "pct_of_recipe": 9.5
                }
            ],
            "structure_snapshot": {
                "has_main_protein": true,
                "has_calcium_source": true,
                "has_omega3_support": false,
                "has_carbohydrate_source": true,
                "has_vegetable": true,
                "has_liver": true
            }
        }

#### ingredients
            字段	必填	来源	给LLM
            ingredient_name	✅	Enrich	✅
            weight_grams	✅	Normalizer	❌
            pct_of_recipe	✅	Derived	✅
            grams_per_kg_bw	⚠️	Derived	✅
            food_group	✅	Enrich	✅
            role_tags	❌	Enrich	❌
            risk_tags	❌	Enrich	❌

#### category_totals
            字段	必填	来源	给LLM
            category	✅	Derived	✅
            pct_of_recipe	✅	Derived	✅
        只保留关键 categories 如 fruit, organ_liver, oil等

#### structure_snapshot
            字段	必填	来源	给LLM
            has_main_protein	✅	Derived	❌
            has_calcium_source	✅	Derived	✅
            has_omega3_support	✅	Derived	✅
            has_liver	⚠️	Derived	❌

### formula_review
        {
            "formula_review": {
                "sanity_status": "needs_adjustment",
                "ingredient_realism_flags": [
                "high_fruit_for_small_puppy"
                ],
                "structure_flags": [
                "missing_omega3_support"
                ],
                "review_focus_points": [
                "fruit proportion",
                "calcium balance",
                "omega3 support"
                ]
            }
        }

        字段	必填	来源	给LLM
        sanity_status	✅	Rule	✅
        ingredient_realism_flags	⚠️	Rule	❌
        structure_flags	⚠️	Rule	❌
        review_focus_points	⚠️	Rule	✅

### strength_flags
        [
            {
                "type": "nutritional",
                "code": "strong_protein_support",
                "priority": "high",
                "evidence": {
                "nutrient_id": "protein",
                "value": 55.0,
                "min_required": 45.0,
                "unit": "g"
                }
            },
            {
                "type": "formula_structure",
                "code": "clear_calcium_slot_present",
                "priority": "medium",
                "evidence": {
                "slot_type": "Calcium Slot"
                }
            }
        ]

        字段	必填	来源	给LLM
        code	✅	Rule	❌
        type	⚠️	Rule	❌
        priority	⚠️	Rule	✅
        evidence	⚠️	Rule	❌
### risk_flags

        [
            {
                "type": "nutrient_deficiency",
                "severity": "high",
                "code": "low_calcium",
                "priority": 1,
                "evidence": {
                "nutrient_id": "calcium",
                "value": 0.8,
                "min_required": 1.0,
                "unit": "g"
                },
                "recommended_action_code": "increase_calcium_support"
            },
            {
                "type": "ratio_imbalance",
                "severity": "high",
                "code": "ca_p_ratio_below_target",
                "priority": 1,
                "evidence": {
                "ratio_id": "ca_p_ratio",
                "value": 0.9,
                "min_target": 1.0,
                "max_target": 2.0
                },
                "recommended_action_code": "rebalance_calcium_phosphorus"
            },
            {
                "type": "ingredient_amount",
                "severity": "medium",
                "code": "high_blueberry_for_small_puppy",
                "priority": 2,
                "evidence": {
                "ingredient_name": "Blueberry",
                "weight_grams": 40.0,
                "grams_per_kg_bw": 8.0,
                "life_stage": "DOG_PUPPY",
                "body_weight_kg": 5.0
                },
                "recommended_action_code": "reduce_fruit_proportion"
            }
        ]
    
        字段	必填	来源	给LLM
        code	✅	Rule	❌
        severity	✅	Rule	✅
        priority	✅	Rule	✅
        evidence	⚠️	Rule	❌
        recommended_action_code	⚠️	Rule	❌
### feeding_guidance_flags
        [
            {
                "type": "feeding_strategy",
                "code": "split_into_3_meals_for_small_puppy"
            },
            {
                "type": "transition",
                "code": "gradual_transition_5_7_days"
            },
            {
                "type": "monitoring",
                "code": "watch_stool_quality"
            },
            {
                "type": "monitoring",
                "code": "monitor_body_weight_and_condition"
            }
        ]

        字段	必填	来源	给LLM
        code	✅	Rule	❌
        priority	⚠️	Rule	✅
### explanation_policy

        字段	必填	来源	给LLM
        tone	✅	固定	✅
        max_strengths	✅	固定	✅
        max_risks	✅	固定	✅
        max_guidance_items	✅	固定	✅
        no_medical_claims	✅	固定	✅
        rule_engine_is_source_of_truth	✅	固定	✅
        language (后续多语言扩展时 Context 层只需改这一个字段，Prompt 不用动)

## 各层功能

### Normalization
    把前端 explain 请求，转成统一内部格式。
#### Input
    ExplainRecipeRequest
    - pet
    - recipe
#### Output
    NormalizedExplainInput
#### Function
    这一层不做规则判断，只做“洗干净输入”
    - 统一字段命名
        例如 weight_kg / weight_kg → body_weight_kg
    - 统一 life stage 枚举
        你当前后端里有 DOG_ADULT / DOG_PUPPY / DOG_SENIOR 以及 energy calculator 返回的 life_stage。
    - 统一 nutrient id 映射
        处理空值
    - 统一数值类型

### Enrich
    把 recipe 里的 ingredient 变成 explain 可判断对象。

#### 输入

- `NormalizedExplainInput`
- 数据库查询结果：ingredients + ingredient_tags

#### 输出

- `EnrichedExplainInput`    

#### 要做的事

按 `ingredient_id` 查：

- `food_group`
- `max_g_per_kg_bw`
- `max_pct_kcal`
- `role_tags`
- `risk_tags`
- `note_tags`

还可以顺手补：

- `slot_type`(可选)

#### 备注

    如果某 ingredient 查不到 enrich 信息，也不要报错，保留一个降级版本继续走。

### 派生指标 derived metrics
把“原始 recipe 数据”变成“可解释数据”。

#### 输入

- `EnrichedExplainInput`

#### 输出

- `DerivedMetrics`

#### 建议必算字段

- `grams_per_kg_bw`
这个定义对“小体型幼犬 + 某食材过量”的判断非常关键。
- `pct_of_recipe`
- `category_totals`
- `supplement_count`
- `non_supplement_count`
- `ca_p_ratio`
- `has_main_protein`
- `has_calcium_source`
- `has_omega3_support`

#### 备注

顺便生成之前定义的：

- `ingredient_summary.ingredients`
- `ingredient_summary.category_totals`
- `ingredient_summary.structure_snapshot`

### rule engine
这是中间层最核心的一步。

负责把事实和派生指标转成“解释用判断”。

#### 输入

- `EnrichedExplainInput`
- `DerivedMetrics`
- 规则配置

#### 输出

- `nutrition_summary`
- `strength_flags`
- `risk_flags`
- `feeding_guidance_flags`
- `formula_review`

#### 这里要做的判断

#### 1）营养判断

基于 `nutrient_analysis`：

- `level1_findings`
- `flagged_nutrients`
- `ratio_findings`
- `level2_triggered_findings`

你在 `question.md` 里已经把这部分结构整理得很清楚。

#### 2）结构判断

基于 slot/tags/category：

- `clear_main_protein_present`
- `clear_calcium_slot_present`
- `omega3_source_present`
- `missing_calcium_source`
- `missing_omega3_support`

#### 3）现实性判断

基于 grams/kg BW、category 占比、ingredient 上限：

- `high_fruit_for_small_puppy`
- `high_liver_proportion`
- `ingredient_exceeds_g_per_kg_bw_limit`
- `ingredient_exceeds_pct_limit`

#### 4）喂养建议触发

从 risk 和 pet context 推出：

- `split_into_3_meals_for_small_puppy`
- `gradual_transition_5_7_days`
- `watch_stool_quality`
- `monitor_body_weight_and_condition`

### 优先级排序（可选）
规则可以全跑，但不要全部给 LLM。

#### 输入

- `nutrition_summary`
- `strength_flags`
- `risk_flags`
- `feeding_guidance_flags`

#### 输出

- 排序和裁剪后的 explain 候选集合

#### 建议规则

- `key_findings`：最多 4–6 条
- `strengths`：最多 2–3 条
- `risks`：最多 3–5 条
- `feeding_guidance`：每组 2–4 条

#### 备注

**priority 保留在中间层，传给 LLM 可以，但不必向前端暴露。** 这能帮助 LLM决定先说什么。

### token 压缩
把“可解释候选集合”压缩成适合 LLM 的 context。

#### 输入

- 排序后的候选集合

#### 输出

- `RecipeExplanationContext`

#### 具体做法

不要把全量 nutrient_analysis 和所有 ingredients 原样扔给 LLM。

而是只传：

- `pet_context`
- `recipe_context`
- `nutrition_summary`（压缩后）
- `ingredient_summary`（压缩后）
- `formula_review`
- `strength_flags`
- `risk_flags`
- `feeding_guidance_flags`
- `explanation_policy`

#### 压缩原则

- 对一级营养素保留数值
- 对非重点达标项只保留状态或完全不传
- ingredient 只保留最值得解释的几项
- category_totals 只保留高价值类别，例如 fruit / liver / supplement / oil

### fallback 支持
即使 LLM 失败，也能生成一版基础 explain。

#### 输入

- `RecipeExplanationContext`

#### 输出

- 模板化 `RecipeExplanationOutput`

#### 做法

直接根据：

- `overview.status`
- `strength_flags`
- `risk_flags`
- `feeding_guidance_flags`

拼出最小输出。

这也是为什么中间层必须把 rule 和 code 打好，而不是把所有判断都留给 LLM。