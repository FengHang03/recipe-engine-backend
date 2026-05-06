# Recipe Explain 完整版实现路线图

> **当前状态**：MVP Sprint 1 已完成  
> **本文档**：描述从 MVP 到完整产品所需的全部实现内容，按优先级和依赖关系排列

---

## 目录

1. [当前 MVP 已实现内容总览](#1-当前-mvp-已实现内容总览)
2. [Sprint 2 — 食材优化建议（高优先级）](#2-sprint-2--食材优化建议高优先级)
3. [Sprint 3 — 营养深度分析扩展](#3-sprint-3--营养深度分析扩展)
4. [Sprint 4 — 产品体验完善](#4-sprint-4--产品体验完善)
5. [长期路线图](#5-长期路线图)
6. [技术债清单](#6-技术债清单)
7. [各文件待实现内容速查](#7-各文件待实现内容速查)

---

## 1. 当前 MVP 已实现内容总览

### ✅ 已完成

| 模块 | 实现内容 |
|---|---|
| **Layer 1 Normalizer** | 字段重命名、枚举统一、null 安全、fallback 分支完整 |
| **Layer 2 Enrichment** | `ingredients` + `ingredient_tags` 批量查询、tag 规范化映射、双级降级 |
| **Layer 3 DerivedMetrics** | grams/kg BW、coarse category mapping（16 个 FoodGroup）、`PLANT_ANTIOXIDANT` 浆果细分、Ca:P 比值、structure_snapshot（含 slot_type 主判断） |
| **Layer 4 RuleEngine** | 4 个 level1 营养素、Ca:P ratio findings、4 个 deficiency risk flags、5 个 structure flags、3 个 realism rules（含互斥 fruit 规则）、7 个 guidance flags、`FormulaReview` 自动生成 |
| **Layer 5 ContextBuilder** | 纯组装，全量透传 |
| **Layer 6 LLMService** | 两层裁剪、system/user prompt、Anthropic API 调用、JSON 解析、confidence 同步、完整 fallback（含 key_findings、readable titles、severity 排序） |
| **Router** | FastAPI 端点 `POST /recipes/explain`，LLM 失败返回 200+fallback |

### ❌ 明确不在 MVP 范围

- `IngredientAdjustmentIdea` 填充（gap_analysis 依赖后端）
- `pct_of_recipe > max_pct_kcal` 规则（percentage 字段统一后）
- 多语言支持
- `health_conditions` 适配规则
- `level2_triggered_findings`

---

## 2. Sprint 2 — 食材优化建议（高优先级）

**前置条件**：后端提供 `gap_analysis` 接口，返回各营养素缺口量及对应补充食材估算。

### 2.1 激活 `IngredientAdjustmentIdea`

**涉及文件**：`rule_engine/engine.py`、`rule_engine/static_candidates.py`、`models.py`、`context_builder.py`、`llm_service.py`

**需要实现：**

```
rule_engine/engine.py:
  - 新增 _build_adjustment_ideas() 函数
  - 输入：risk_flags + gap_analysis（来自后端新接口）
  - 逻辑：遍历 risk_flags 的 recommended_action_code
          → 查 ACTION_TO_CANDIDATE 映射
          → 从 STATIC_CANDIDATES 取候选食材列表
          → 生成 IngredientAdjustmentIdea(kind="addition", ...)
  - 输出填入 RuleEngineResult.ingredient_adjustment_ideas

models.py:
  - RecipeExplanationContext 新增字段：
    improvement_suggestions: Optional[List[IngredientAdjustmentIdea]] = None

context_builder.py:
  - build_context() 传入 rule_result.ingredient_adjustment_ideas
    到 context.improvement_suggestions

llm_service.py:
  - _build_user_prompt() 新增 [ADJUSTMENT IDEAS] section
  - _parse_llm_response() 解析 ingredient_adjustment_ideas
  - generate_fallback_output() 从 context.improvement_suggestions
    生成 IngredientAdjustmentIdeasOutput
  - JSON schema 新增：
    "ingredient_adjustment_ideas": {
      "additions":     [{"ingredient": "...", "reason": "...", "estimated_amount": "..."}],
      "replacements":  [{"replace": "...", "with": "...", "reason": "..."}]
    }
```

### 2.2 调整量具体建议（`adjustment_detail`）

**前置条件**：后端 gap_analysis 返回 `calcium_gap_g`、`to_close_with_{ingredient}_g` 等字段。

```
IngredientAdjustmentIdea.adjustment_detail 从 None 填充为实际数据：
  {
    "nutrient": "calcium",
    "current_value": 0.8,
    "target_value": 1.0,
    "gap": 0.2,
    "suggested_ingredient": "Eggshell Powder",
    "suggested_amount_g": 1.5
  }
```

### 2.3 `pct_of_recipe > max_pct_kcal` 规则激活

**前置条件**：`percentage` 字段在全系统统一为 `pct_of_recipe`（确认后端已对齐）。

```
realism_rules.py:
  - 在 run() 末尾取消 TODO 注释，添加：
    if (m.enrich_available
        and m.max_pct_kcal is not None
        and m.pct_of_recipe > m.max_pct_kcal
        and "ingredient_exceeds_pct_limit" not in seen_codes):
      flags.append(RiskFlag(
          type="ingredient_amount",
          severity="medium",
          code="ingredient_exceeds_pct_limit",
          priority=3,
      ))

engine.py:
  - _KEY_CONCERN_MAP 新增：
    "ingredient_exceeds_pct_limit": "One or more ingredients exceed the recommended caloric proportion"

guidance_rules.py:
  - _STOOL_TRIGGER_CODES 添加 "ingredient_exceeds_pct_limit"
```

---

## 3. Sprint 3 — 营养深度分析扩展

### 3.1 Level2 营养素分析（`level2_triggered_findings`）

**触发条件**：基于 risk_tags（如 `risk_high_vita`、`risk_high_copper`）或 nutrient_analysis 中的特定营养素超标。

```
models.py:
  - NutritionSummary 启用 level2_triggered_findings 字段：
    level2_triggered_findings: List[Level2Finding] = Field(default_factory=list)

  - 新增 Level2Finding 类：
    class Level2Finding(BaseModel):
        nutrient_id: str
        display_name: str
        status: str           # "high" | "risk_tag_triggered"
        severity: str         # "high" | "medium"
        reason_code: str

rule_engine/nutrition_rules.py:
  - 新增 _evaluate_level2() 函数
  - 遍历 enriched_ingredients 的 risk_tags：
    - risk_high_vita     → level2 finding: Vitamin A excess risk
    - risk_high_copper   → level2 finding: Copper excess risk
    - risk_high_iodine   → level2 finding: Iodine excess risk
    - risk_high_selenium → level2 finding: Selenium excess risk
    - risk_high_sodium   → level2 finding: Sodium excess risk
    - risk_high_vit_d    → level2 finding: Vitamin D excess risk
  - 同时生成对应 RiskFlag（type="nutrient_excess"）

engine.py:
  - _KEY_CONCERN_MAP 新增 level2 risk codes
  - ContextBuilder 和 LLMService prompt 中添加 level2 section
```

### 3.2 氨基酸完整性评估

**前置条件**：营养素数据库包含关键氨基酸数据（赖氨酸、蛋氨酸、色氨酸等）。

```
新增 rule_engine/amino_acid_rules.py:
  - 判断关键氨基酸是否达到 NRC 最低需求
  - 生成 AminoAcidFinding 和对应 RiskFlag
  - code: "low_lysine", "low_methionine", "low_tryptophan"

models.py:
  - NutritionSummary 新增 amino_acid_findings: List[AminoAcidFinding]
```

### 3.3 脂肪酸平衡分析

```
新增 rule_engine/fatty_acid_rules.py:
  - omega6/omega3 比值计算（理想范围 5:1 到 10:1）
  - 基于 role_omega6_la 和 role_omega3_* 的食材组合判断
  - 生成 RatioFinding（ratio_id="omega6_omega3_ratio"）

models.py:
  - RatioFinding 支持新的 ratio_id
  - NutritionSummary.ratio_findings 扩展
```

---

## 4. Sprint 4 — 产品体验完善

### 4.1 多语言支持

**前置条件**：确认目标语言（中文/英文）。

```
models.py:
  - ExplanationPolicy.language 从 "en" 改为可配置

llm_service.py:
  - _build_system_prompt() 根据 policy.language 切换提示语言
  - CODE_TO_READABLE、_STRENGTH_CODE_TO_TITLE、_RISK_CODE_TO_TITLE
    改为按语言索引的 dict：
    CODE_TO_READABLE = {
        "en": {...},
        "zh": {...},
    }

router.py:
  - 从 Accept-Language header 或请求体读取语言偏好
  - 传入 ExplanationPolicy(language="zh")
```

### 4.2 `health_conditions` 规则适配

**前置条件**：兽医营养规则库完成。

```
新增 rule_engine/health_rules.py:
  - 根据 health_conditions 列表调整规则阈值或添加专属 risk_flags：
    - "obesity"       → 降低热量目标，fat 上限收紧
    - "kidney_disease"→ phosphorus 上限收紧，protein 来源限制
    - "diabetes"      → carb 比例限制
    - "pancreatitis"  → fat 上限收紧

engine.py:
  - run() 中在 guidance_rules 之后调用 health_rules.run()
  - 将 health risk flags 合并到 all_risk_flags
```

### 4.3 过敏食材检测

```
新增 rule_engine/allergy_rules.py:
  - 遍历 enriched_ingredients，检查 ingredient_name 是否在 allergies 列表中
  - 生成 RiskFlag(type="allergen", severity="high", code="allergen_detected")
  - key_concern: "{ingredient_name} is listed as an allergen for this dog"

guidance_rules.py:
  - 新增触发：存在 allergen_detected risk → guidance "avoid_allergen_ingredient"
```

### 4.4 JSON 解析稳健性提升

当前 `call_llm()` 使用简单的 `removeprefix/removesuffix` 处理 fence。

```
llm_service.py:
  - 实现更稳健的 _extract_json() 函数：
    1. 尝试直接 json.loads(raw)
    2. 用正则提取 ```json ... ``` 或 ``` ... ``` 块
    3. 尝试找到第一个 { 到最后一个 } 的范围直接解析
    4. 全部失败 → raise，触发 fallback

  def _extract_json(raw: str) -> dict:
      import re
      # 1. direct parse
      try: return json.loads(raw.strip())
      except: pass
      # 2. fenced block
      m = re.search(r'```(?:json)?\s*([\s\S]+?)```', raw)
      if m:
          try: return json.loads(m.group(1).strip())
          except: pass
      # 3. first { to last }
      start = raw.find('{')
      end   = raw.rfind('}')
      if start != -1 and end != -1:
          try: return json.loads(raw[start:end+1])
          except: pass
      raise ValueError("Cannot extract JSON from LLM response")
```

### 4.5 Prompt 版本管理

```
llm_service.py:
  - 新增 PROMPT_VERSION = "1.1"
  - MetaOutput 新增 prompt_version: str 字段
  - 方便 A/B 测试不同 prompt 版本的输出质量
```

---

## 5. 长期路线图

### 5.1 与兽医协作接口

```
新增 router.py endpoint: POST /recipes/explain/share
  - 生成可分享的 explain 报告（PDF / URL）
  - 支持兽医批注（comment fields on RiskOutput）
  - 兽医可标记 "confirmed" / "override" 某条 risk

models.py:
  - RiskOutput 新增：
    vet_review: Optional[str] = None   # "confirmed" | "overridden" | None
    vet_note: Optional[str] = None
```

### 5.2 历史趋势对比

```
新增 router.py endpoint: POST /recipes/explain/compare
  - 输入：当前食谱 + 历史食谱列表
  - 对比 key_findings 变化趋势
  - 生成 trend_assessment: 营养状态是否在改善

新增 TrendAnalysis 模型：
  class NutrientTrend(BaseModel):
      nutrient_id: str
      trend: str    # "improving" | "stable" | "declining"
      previous_status: str
      current_status: str
```

### 5.3 自动食谱优化建议（AI 生成版本）

当前 `IngredientAdjustmentIdeasOutput.replacements` 为空。

```
未来实现：
  - 基于 gap_analysis + STATIC_CANDIDATES，让 LLM 生成具体的"优化版食谱"
  - 在 prompt 中传入当前食谱 + 缺口 + 候选食材
  - LLM 返回调整后的食材比例建议
  - 需要后端验证 LLM 生成的食谱是否仍满足 AAFCO 标准
```

---

## 6. 技术债清单

| 项目 | 优先级 | 影响范围 |
|---|---|---|
| `get_db` 占位符替换为实际 DB session factory | 🔴 必须（上线前） | `router.py` |
| `call_llm()` JSON 提取稳健性 | 🟡 建议 Sprint 2 | `llm_service.py` |
| `CODE_TO_READABLE` 缺少 `high_fruit_proportion` 的 `reduce_fruit_proportion` 触发文案区分 | 🟡 建议 | `guidance_rules.py` |
| `IngredientSummaryItem.risk_tags` 在 LLM prompt 中始终排除 | 🟢 下个 sprint 展示层使用时处理 | `llm_service.py` |
| `_COARSE_CATEGORY_MAP` 未覆盖的 FoodGroup 返回 `"other"` — 建议添加监控告警 | 🟢 监控 | `derived_metrics.py` |
| `_ROLE_TAG_MAP` 未知 tag 只做 `debug` log — 建议定期审查 DB 新增 tag | 🟢 监控 | `enrichment.py` |
| Prompt 版本号管理 | 🟢 长期 | `llm_service.py` |

---

## 7. 各文件待实现内容速查

### models.py
- `NutritionSummary.level2_triggered_findings` 字段启用
- 新增 `Level2Finding` 类
- `RecipeExplanationContext.improvement_suggestions` 字段
- `IngredientAdjustmentIdea.adjustment_detail` 从 `None` 改为实际类型
- `NutrientTrend`、`TrendAnalysis` 类（Sprint 5.2）

### enrichment.py
- 无需改动（`max_pct_kcal` 已查询，等激活）

### derived_metrics.py
- 无需改动（`max_pct_kcal` 已透传到 `EnrichedIngredient`）

### rule_engine/nutrition_rules.py
- `_evaluate_level2()` 函数（Sprint 3.1）
- 氨基酸评估扩展（Sprint 3.2）

### rule_engine/structure_rules.py
- 无待办

### rule_engine/realism_rules.py
- `pct_of_recipe > max_pct_kcal` 规则取消注释激活（Sprint 2.3）

### rule_engine/guidance_rules.py
- `_STOOL_TRIGGER_CODES` 添加 `ingredient_exceeds_pct_limit`（Sprint 2.3）
- `CODE_TO_READABLE` 添加 `allergen_detected` 等新 code（Sprint 4.3）

### rule_engine/engine.py
- `_build_adjustment_ideas()` 函数（Sprint 2.1）
- `_KEY_CONCERN_MAP` 扩展（随 Sprint 2/3 新增 code）

### rule_engine/static_candidates.py
- `STATIC_CANDIDATES` 随实际食材库扩展
- 激活后迁移到 DB（长期）

### rule_engine/ — 新增文件
- `health_rules.py`（Sprint 4.2）
- `allergy_rules.py`（Sprint 4.3）
- `amino_acid_rules.py`（Sprint 3.2）
- `fatty_acid_rules.py`（Sprint 3.3）

### context_builder.py
- `improvement_suggestions` 字段传入（Sprint 2.1）

### llm_service.py
- `_extract_json()` 稳健 JSON 提取（Sprint 4.4）
- Prompt 中添加 `[ADJUSTMENT IDEAS]` section（Sprint 2.1）
- `generate_fallback_output()` 从 `improvement_suggestions` 生成 `IngredientAdjustmentIdeasOutput`（Sprint 2.1）
- 多语言 prompt 切换（Sprint 4.1）
- Prompt 版本管理（Sprint 4.5）

### router.py
- `get_db` 替换为实际 DB session factory（上线前必须）
- `POST /recipes/explain/share`（Sprint 5.1）
- `POST /recipes/explain/compare`（Sprint 5.2）
