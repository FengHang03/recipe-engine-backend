contracts/：Pydantic 模型、枚举、输入输出契约
orchestration/：流程编排、mode 分发、service facade
engines/：真正干活的算法引擎（L1/L2/scaling/rule engine）
infra/：数据库读取、外部 API、repository、mappers

1. 这个目录负责什么

先用 3–6 句话说清楚：

这个目录的核心职责
它在整个系统里的位置
它解决什么问题

比如 recipe_generation/ 的 README 开头可以写：

负责生成 recipe weights 和 nutrient analysis
支持 fixed set optimization / user-defined optimization / preset scaling
不负责 explain 文案生成
不直接处理 HTTP request

这一段最重要，因为它定义“边界”。

2. 这个目录不负责什么

这一段特别重要，尤其对 AI。

因为 AI 最容易犯的错不是“看不懂”，而是“看懂一点后顺手改错地方”。

所以 README 里最好明确写：

不负责数据库 schema 迁移
不负责前端展示 shape patching
不负责 LLM 文案生成
不负责持久化用户偏好

这会明显减少误改。

3. 目录结构一览

给出本目录下的文件树，简短说明每个文件做什么。

例如：

contracts/
├── enums.py         # shared recipe-generation enums
├── shared.py        # shared domain models
├── requests.py      # top-level request models
├── recipe_specs.py  # recipe specification objects
└── constraints.py   # constraint model definitions

这个非常适合 AI。

4. 核心流程 / 数据流

这一段用最短路径把“输入如何流到输出”讲清楚。

例如：

RecipeGenerationRequest
  -> generate_recipe_service
  -> mode-specific engine
  -> nutrient_analyzer
  -> RecipeGenerationResult
  -> explain_payload_builder (optional)

或者 explain 目录里写：

ExplainRecipeRequest
  -> normalize
  -> enrich
  -> derived_metrics
  -> rule_engine
  -> context_builder
  -> llm_service
  -> RecipeExplanationOutput

这个比大段文字更有效。

5. 主要输入输出契约

这部分不用把所有字段全抄一遍，而是写：

本目录最重要的 2–5 个模型
它们之间是什么关系
哪个是入口，哪个是出口

例如：

RecipeGenerationRequest 是 orchestration 层统一入口
RecipeCombinationSpec / UserDefinedRecipeSpec / PresetRecipeSpec 是三种 recipe source payload
RecipeGenerationResult 是统一结果模型
WeightedIngredient / NutrientAnalysis 是结果组件
6. 最小示例

这里最适合放 JSON code block。

比如一个最小 request：

{
  "mode": "optimize_user_defined",
  "pet_profile": {
    "species": "dog",
    "life_stage": "adult",
    "weight_kg": 20,
    "daily_calories_kcal": 900
  },
  "user_defined_spec": {
    "spec_id": "manual_001",
    "selected_items": [
      {
        "ingredient": {
          "ingredient_id": "salmon",
          "name": "Salmon",
          "food_group": "PROTEIN_FISH"
        },
        "chosen_slot": "main_protein"
      }
    ]
  }
}

再放一个最小 result：

{
  "mode": "optimize_user_defined",
  "status": "OPTIMAL",
  "total_weight_grams": 540.0,
  "weights": [
    {
      "ingredient_id": "salmon",
      "ingredient_name": "Salmon",
      "slot_type": "main_protein",
      "weight_grams": 320.0,
      "pct_of_recipe": 59.3
    }
  ],
  "nutrient_analysis": []
}

这个比纯字段列表更直观。

7. 设计约束 / 约定

这部分非常值钱。可以写“这个目录内部默认遵循什么规则”。

比如：

所有 domain models 使用 Pydantic
所有 contracts 不直接 import pandas DataFrame
所有 engine 不直接依赖 FastAPI request objects
所有 new enums 优先评估是否进入 shared/enums.py
所有 explain-facing result 必须能映射到 RecipeGenerationResult

这会让整个项目更稳。

8. 修改时注意事项

这一段很适合提醒未来的你和 AI：

例如：

改 SlotType 时，要同步检查 L1 / L2 / explain / preset template
改 RecipeGenerationResult 时，要同步检查 explain adapter 和前端结果页
改 ConstraintProfile 时，不要直接改 AAFCO hard limits
改 IngredientRef 字段名时，要检查 repository mapper

这种“改这里会影响谁”的说明非常重要。

你可以直接全项目复用这个模板。

# <Directory Name>

## Responsibility
This directory is responsible for:
- ...
- ...

It is part of:
- ...

## Out of Scope
This directory does not:
- ...
- ...

## File Layout
```text
<tree>
Core Flow
<input> -> <step> -> <step> -> <output>
Key Contracts
ModelA: ...
ModelB: ...
ModelC: ...
Minimal Input Example
{ ... }
Minimal Output Example
{ ... }
Invariants / Rules
...
...
...
Change Impact

If you change:

X, also check ...
Y, also check ...

这个模板对 AI 特别友好，因为它把信息固定到了几个稳定位置。

---

# 四、不同层级 README 应该写到什么粒度

## 1. 顶层 domain README
例如：
- `domains/recipe_generation/README.md`
- `domains/explain/README.md`

这里写：
- 这个 domain 的整体目标
- 子目录怎么分工
- 主流程
- 和其他 domain 的边界

### 不要写太细的字段表  
因为这些会过时。

---

## 2. 子目录 README
例如：
- `contracts/README.md`
- `orchestration/README.md`
- `engines/l2/README.md`

这里写：
- 这个子层的职责
- 哪些文件最关键
- 输入输出模型
- 修改注意事项

这是最值钱的一层。

---

## 3. 单文件说明
对于特别核心的文件，比如：
- `generate_recipe_service.py`
- `llm_service.py`
- `l2_engine.py`

更适合在文件头 docstring 中写：
- 责任
- 输入
- 输出
- 不负责什么

而不是给每个文件都再配 README。

---

# 五、针对你项目，我建议至少放这些 README

如果你不想太重，我建议最少放这几个：

```text
app/
├── README.md
├── shared/
│   └── README.md
├── domains/
│   ├── recipe_generation/
│   │   ├── README.md
│   │   ├── contracts/
│   │   │   └── README.md
│   │   ├── orchestration/
│   │   │   └── README.md
│   │   └── engines/
│   │       ├── README.md
│   │       └── l2/
│   │           └── README.md
│   └── explain/
│       ├── README.md
│       ├── contracts/
│       │   └── README.md
│       └── pipeline/
│           └── README.md

这样已经足够强了。