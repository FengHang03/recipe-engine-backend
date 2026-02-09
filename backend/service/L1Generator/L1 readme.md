# L1 Recipe Generator - 完整文档

## 📋 目录

1. [系统概述](#系统概述)
2. [架构设计](#架构设计)
3. [文件说明](#文件说明)
4. [快速开始](#快速开始)
5. [配置详解](#配置详解)
6. [API参考](#api参考)
7. [常见问题](#常见问题)

---

## 系统概述

L1 Recipe Generator 是宠物食谱优化系统的**第一层 - 组合筛选层**。

### 核心功能

1. **食材筛选** - 根据槽位配置筛选符合条件的食材
2. **动态调度** - 根据依赖规则动态启用/禁用槽位
3. **组合生成** - 穷举所有可能的食材组合
4. **多样性控制** - 避免同类食材重复
5. **风险控制** - 应用互斥规则限制高风险食材

### 输出

L1 输出 `RecipeCombination` 对象列表，每个组合包含:
- 选定的食材列表 (按槽位分组)
- 评分指标 (多样性、风险、完整性)
- 元数据 (启用的槽位、应用的规则)

这些组合将传递给 **L2 层 (数值优化层)** 计算每种食材的具体用量。

---

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    L1 Recipe Generator                   │
│                                                           │
│  ┌────────────────┐      ┌──────────────────┐          │
│  │   L1Config     │─────▶│  SlotScheduler   │          │
│  │  (配置系统)     │      │  (槽位调度器)     │          │
│  └────────────────┘      └────────┬─────────┘          │
│           │                       │                      │
│           │                       │                      │
│           ▼                       ▼                      │
│  ┌────────────────────────────────────────────┐        │
│  │        CombinationGenerator                 │        │
│  │        (组合生成器)                          │        │
│  │                                              │        │
│  │  - 递归回溯生成组合                           │        │
│  │  - 应用互斥规则剪枝                           │        │
│  │  - 计算多样性/风险评分                        │        │
│  └────────────────┬───────────────────────────┘        │
│                   │                                      │
│                   ▼                                      │
│         ┌─────────────────────┐                         │
│         │ RecipeCombination[] │ ────────────┐          │
│         │  (候选组合列表)      │              │          │
│         └─────────────────────┘              │          │
└──────────────────────────────────────────────┼──────────┘
                                                │
                                                │
                                                ▼
                                    ┌──────────────────┐
                                    │  L2 Optimizer    │
                                    │  (数值优化层)     │
                                    └──────────────────┘
```

### 核心类

#### 1. `L1Config`
- **作用**: 定义槽位配置、筛选规则、依赖关系、互斥规则
- **位置**: `l1_config.py`

#### 2. `SlotScheduler`
- **作用**: 管理槽位状态，根据依赖规则动态启用/禁用槽位
- **关键方法**:
  - `apply_dependencies()` - 应用依赖规则
  - `get_slot_candidates()` - 获取槽位候选食材
  - `select_ingredients_for_slot()` - 为槽位选择食材并触发规则

#### 3. `CombinationGenerator`
- **作用**: 生成所有可能的食材组合
- **关键方法**:
  - `generate_combinations()` - 主入口
  - `_backtrack()` - 递归回溯算法
  - `_score_combinations()` - 计算评分

#### 4. `L1RecipeGenerator`
- **作用**: 主入口类，整合所有组件
- **关键方法**:
  - `generate()` - 生成组合
  - `export_combinations_summary()` - 导出摘要

---

## 文件说明

### 核心文件

| 文件 | 说明 |
|------|------|
| `l1_config.py` | 配置系统 - 定义槽位、规则、枚举 |
| `l1_recipe_generator.py` | 核心逻辑 - 调度器和生成器 |
| `data_loader.py` | 数据加载 - 从数据库读取食材和营养数据 |
| `l1_example_usage.py` | 使用示例 - 展示各种用法 |

### 数据流

```
Google Cloud SQL
      │
      ▼
data_loader.py (加载食材数据)
      │
      ▼
pd.DataFrame (ingredients_df)
      │
      ▼
l1_recipe_generator.py (生成组合)
      │
      ▼
RecipeCombination[] (候选组合)
      │
      ▼
L2 Optimizer (数值优化)
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install pandas pydantic sqlalchemy psycopg2-binary
```

### 2. 配置数据库连接

```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

### 3. 基础使用

```python
from data_loader import IngredientDataLoader
from l1_recipe_generator import L1RecipeGenerator

# 1. 加载数据
loader = IngredientDataLoader()
ingredients_df = loader.load_ingredients_for_l1()

# 2. 创建生成器
l1_generator = L1RecipeGenerator(ingredients_df)

# 3. 生成组合
combinations = l1_generator.generate(max_combinations=500)

# 4. 查看结果
summary = l1_generator.export_combinations_summary(combinations, top_n=10)
print(summary)

# 5. 传递给 L2
for combo in combinations[:10]:
    ingredient_ids = combo.get_ingredient_ids()
    # 调用 L2 优化器...
```

---

## 配置详解

### 内脏分类方案 (3-subgroup)

```
1. ORGAN_LIVER (肝脏组)
   - liver (肝脏)
   - L2约束: Max 5% (维生素A风险)

2. ORGAN_SECRETING (分泌型内脏组)
   - kidney (肾脏)
   - spleen (脾脏)
   - brain (脑花)
   - other_secreting (胰腺、睾丸)
   - L2约束: Max 5% Combined (这组总共最多5%)
   - 个体约束: spleen ≤3%, brain ≤3%

3. ORGAN_MUSCULAR (肌肉型内脏组)
   - heart (心脏)
   - gizzard (胗)
   - other_muscular (舌、肺、肚)
   - L2约束: No Limit (Count as Meat)
```

### 槽位类型

#### 必选槽位 (is_mandatory_default=True)
- `main_protein` - 主蛋白质来源
- `calcium` - 钙源
- `organ_liver` - 肝脏
- `organ_secreting` - 分泌型内脏
- `iodine` - 碘源
- `vegetable` - 蔬菜
- `omega3_lc` - Omega-3 长链脂肪酸
- `omega6_la` - Omega-6 亚油酸

#### 条件启用槽位
根据已选食材动态决定是否启用

#### 可选槽位 (is_mandatory_default=False)
- `carbohydrate` - 碳水化合物
- `fiber` - 纤维
- `organ_muscular` - 肌肉型内脏
- `optional_supplements` - 其他补充剂

### 依赖规则示例

```python
# 规则1: 油鱼跳过鱼油
if main_protein.has_tag("role_omega3_lc"):
    disable("omega3_lc")

# 规则2: 瘦肉强制碳水
if main_protein.subgroup == "meat_lean":
    enable("carbohydrate")

# 规则3: 无碳水必选纤维
if not active("carbohydrate"):
    enable("fiber")
```

### 互斥规则示例

```python
# 规则1: 肝脏最多1个
ExclusionRule(
    target_groups=[FoodGroup.ORGAN_LIVER],
    max_count=1
)

# 规则2: 肝脏+分泌型内脏总共最多2个
ExclusionRule(
    target_groups=[
        FoodGroup.ORGAN_LIVER,
        FoodGroup.ORGAN_SECRETING
    ],
    max_count=2
)
```

---

## API参考

### L1RecipeGenerator

```python
class L1RecipeGenerator:
    def __init__(
        self,
        ingredients_df: pd.DataFrame,
        config: Optional[L1Config] = None
    )
    
    def generate(
        self,
        max_combinations: int = 500,
        dog_profile: Optional[Dict] = None
    ) -> List[RecipeCombination]
    
    def export_combinations_summary(
        self,
        combinations: List[RecipeCombination],
        top_n: int = 10
    ) -> pd.DataFrame
```

### RecipeCombination

```python
@dataclass
class RecipeCombination:
    combination_id: str
    ingredients: Dict[str, List[Ingredient]]
    diversity_score: float
    risk_score: float
    completeness_score: float
    active_slots: List[str]
    
    def get_all_ingredients() -> List[Ingredient]
    def get_ingredient_ids() -> List[str]
```

### Dog Profile 结构

```python
dog_profile = {
    'name': str,
    'weight_kg': float,
    'age_years': int,
    'conditions': List[str],  # ['hyperlipidemia', 'kidney_disease', ...]
    'allergies': List[str],   # ['chicken', 'beef', ...]
    'preferences': Dict
}
```

---

## 常见问题

### Q1: 为什么生成的组合数少于 max_combinations?

**原因:**
1. 食材数量有限
2. 互斥规则过于严格
3. 依赖规则禁用了太多槽位

**解决方案:**
- 检查互斥规则是否过严
- 增加数据库中的食材种类
- 调整 `max_items` 允许更多选择

### Q2: 如何添加新的依赖规则?

在 `SlotScheduler.apply_dependencies()` 中添加:

```python
# 示例: 添加新规则 - 如果选了鱼就不要鸡蛋
if main_protein and main_protein[0].food_group == "PROTEIN_FISH":
    self.set_slot_active("egg", False, "选了鱼,跳过鸡蛋")
```

### Q3: 如何修改内脏的用量限制?

L1 只负责"选什么"，用量限制在 **L2 层** 实现:

```python
# L2 约束示例
liver_weight <= total_weight * 0.05
secreting_weight <= total_weight * 0.05
```

但可以在 `ingredients` 表中设置 `max_pct_kcal`:

```sql
UPDATE ingredients 
SET max_pct_kcal = 0.03 
WHERE food_subgroup = 'spleen';  -- 脾脏最多3%
```

### Q4: 如何排除特定食材?

**方法1: 通过 dog_profile**
```python
dog_profile = {
    'allergies': ['chicken'],  # 排除所有鸡肉
    'conditions': ['hyperlipidemia']  # 排除高胆固醇食材
}
```

**方法2: 修改配置**
```python
config = L1Config()
config.slots["main_protein"].filters.excluded_tags.append("allergen_chicken")
```

**方法3: 在数据库中标记**
```sql
UPDATE ingredients 
SET is_active = FALSE 
WHERE description LIKE '%chicken%';
```

### Q5: 组合生成太慢怎么办?

**优化策略:**
1. **减少 max_combinations**
   ```python
   combinations = l1_generator.generate(max_combinations=200)
   ```

2. **减少每个槽位的 max_items**
   ```python
   config.slots["vegetable"].max_items = 1  # 从2改为1
   ```

3. **增加互斥规则** (减少搜索空间)

4. **启用剪枝优化**
   ```python
   generator.generate_combinations(enable_pruning=True)  # 默认已启用
   ```

### Q6: 如何调试组合生成过程?

启用 DEBUG 日志:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

查看详细日志:
- 槽位启用/禁用
- 依赖规则触发
- 互斥规则检查
- 候选食材筛选

---

## 部署到 Google Cloud Run

### 1. 创建 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### 2. 创建 requirements.txt

```
pandas==2.0.3
pydantic==2.5.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
```

### 3. 部署

```bash
# 构建镜像
gcloud builds submit --tag gcr.io/PROJECT_ID/l1-recipe-generator

# 部署到 Cloud Run
gcloud run deploy l1-recipe-generator \
  --image gcr.io/PROJECT_ID/l1-recipe-generator \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=$DATABASE_URL
```

---

## 下一步

1. ✅ **L1 完成** - 组合生成层
2. ⬜ **实现 L2** - 数值优化层 (线性规划)
3. ⬜ **集成 L1+L2** - 完整食谱生成流程
4. ⬜ **添加 Web API** - RESTful 接口
5. ⬜ **前端界面** - 用户交互

---

## 联系与支持

如有问题，请查看:
- 使用示例: `l1_example_usage.py`
- 配置文档: `l1_config.py`
- 内脏分类决策: `organ_decision_final.md`

祝使用愉快! 🐶