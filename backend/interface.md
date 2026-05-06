# Frontend Interface

- **PetProfile**

```python
@dataclass
class PetProfile:
    """宠物画像"""
    daily_calories_kcal: float          # 目标热量 (kcal/day)
    weight_kg: float              # 体重 (kg)
    life_stage: LifeStage           # 生命阶段
    
    # 可选字段
    allergies: List[str] = field(default_factory=list)
    size_class: Optional[str] = "medium"
    activity_level: Optional[str] = None
    health_conditions: List[str] = field(default_factory=list)
    sterilization_status:Optional[SterilizationStatus] = 'intact'
    repro_status: Optional[ReproductiveStage] = None
```

# Backend

## Main - FastAPI

---

### 1. Calculate Energy

**Endpoint**

- **POST /api/calculate-energy — 能量计算**

**Description**

- **Calculate required energy based on pet profile.**

**触发时机**：`AddPetForm` 表单任意字段变化时自动触发（debounce 600ms）。

---

#### 请求

**URL**：`POST /api/calculate-energy`

**Content-Type**：`application/json`

```tsx
// 前端发送的请求体（EnergyCalculationRequest）
{
  weight_kg:           number;    // 必填，体重 kg，> 0
  species:             string;    // 必填，固定为 "dog"
  age_months:          number;    // 必填，月龄，>= 1
  activity_level:      string;    // 必填，见 ActivityLevel 枚举
  sterilization_status: string;    // 必填，见 SterilizationStatus 枚举
  reproductive_stage:         string;    // 必填，见 ReproductiveStage 枚举
  breed?:              string;    // 可选，品种名称
  lactation_week?:     number;    // 可选，哺乳周数（1-8），reproductive_stage="lactating" 时有效
  nursing_count?:      number;    // 可选，哺乳幼崽数量，reproductive_stage="lactating" 时有效
  senior_month?:       number;    // 可选，老年起始月龄，前端根据 size_class 推算
}
```

<aside>
💡

可以添加 size_class

</aside>

**示例请求体**：

```json
{
  "weight_kg": 20,
  "species": "dog",
  "age_months": 24,
  "activity_level": "moderate",
  "sterilization_status": "intact",
  "reproductive_stage": "none",
  "breed": "Labrador",
  "senior_month": 96
}
```

---

#### 响应

**HTTP 200 OK**

```tsx
// 后端返回（EnergyCalculationResult）
{
  resting_energy_kcal:   number;            // 静息能量需求 kcal/day，保留 1 位小数
  daily_energy_kcal:     number;            // 每日能量需求 kcal/day，保留 1 位小数（前端使用此值）
  life_stage:            string;            // 后端推算的生命阶段，如 "dog_adult"
  model_version:         string;            // 计算器版本，如 "EnergyCalculator-v0.2"
  calculation_breakdown: Record<string, number>; // 计算步骤分解
  warnings:              string[];          // 警告信息，如老年调整提示
}
```

**示例响应**：

```json
{
  "resting_energy_kcal": 782.6,
  "daily_energy_kcal": 1479.2,
  "life_stage": "dog_adult",
  "model_version": "EnergyCalculator-v0.2",
  "calculation_breakdown": {
    "rer": 782.62,
    "life_stage_factor": 1.0,
    "base_der": 782.62,
    "activity_factor_base": 1.8,
    "activity_factor_final": 1.8,
    "breed_factor": 1.05,
    "der_final": 1479.16
  },
  "warnings": []
}
```

**前端使用**：

```tsx
const result = await calculateDailyEnergy(req);
setCalculatedEnergy(result.daily_energy_kcal);  // 作为 daily_calories_kcal 传入食谱生成
```

---

#### 错误响应

| HTTP 状态码 | 原因 |
| --- | --- |
| 422 | 枚举值不合法（如 activity_level 拼错） |
| 500 | 后端计算异常 |

---

### 2. Recipe Generate

**Endpoint**

- **POST /recipes/generate — 食谱生成**

**Description**

- **Generate nutritionally balanced recipes based on AAFCO constraints.**

**触发时机**：用户点击 `AddPetForm` 的 **Generate Recipe** 按钮，或 `Dashboard` 宠物卡片上的 **Generate Recipe** 按钮。

> ⚠️ **注意**：此接口为同步阻塞请求，后端计算需要 **1-3 分钟**。
> 
> 
> Cloud Run 超时设置为 600 秒。前端展示全屏 Loading 遮罩 + 计时器。
> 

---

#### 请求

**URL**：`POST /recipes/generate`

**Content-Type**：`application/json`

```tsx
// 前端发送的请求体（GenerateRecipeRequest）
{
  pet: {
    daily_calories_kcal:      number;    // 必填，由 /api/calculate-energy 返回的 daily_energy_kcal
    weight_kg:          number;    // 必填，体重 kg
    life_stage:           string;    // 必填，后端枚举名称，如 "DOG_ADULT"（大写）
    allergies:            string[];  // 过敏食材列表，无则传 []
    size_class?:          string;    // 可选，如 "medium"
    activity_level?:      string;    // 可选，如 "moderate"
    health_conditions:    string[];  // 健康状况列表，无则传 []
    sterilization_status?: string;    // 可选，如 "intact"
  };
  top_k?: number;                    // 可选，返回食谱数量，默认 5，最大 20
}
```

**life_stage 映射（前端 → 后端）**：

```tsx
// useRecipeGeneration.ts 中的 LIFE_STAGE_MAP
dog: { puppy: "DOG_PUPPY", adult: "DOG_ADULT", senior: "DOG_SENIOR" }
```

**示例请求体**：

```json
{
  "pet": {
    "daily_calories_kcal": 1479.2,
    "weight_kg": 20.0,
    "life_stage": "DOG_ADULT",
    "allergies": [],
    "size_class": "medium",
    "activity_level": "moderate",
    "health_conditions": [],
    "sterilization_status": "intact"
  },
  "top_k": 5
}
```

---

#### 响应

**HTTP 200 OK**

```tsx
// 后端返回（GenerateRecipeResponse）
{
  success:         boolean;       // 是否成功
  total:           number;        // 实际返回食谱数量
  elapsed_seconds: number;        // 后端计算耗时（秒）
  recipes: Array<{
    rank:               number;   // 排名，从 1 开始，1 = 最优
    recipe_id:     string;   // L1 组合 ID
    total_weight_grams: number;   // 食谱总重量（g）
    objective_value:    number | null;  // L2 目标函数值（越大越好）
    used_supplements:   string[];       // 使用的补剂名称列表
    weights: Array<{
      ingredient_id:   string;    // 食材 UUID
      ingredient_name: string;    // 食材名称
      weight_grams:    number;    // 用量（g），保留 2 位小数
      percentage:      number;    // 占总重量百分比，后端已计算
      is_supplement:   boolean;   // 是否为补剂
    }>;
    nutrient_analysis: Array<{
      nutrient_id:          string;         // 营养素小写字符串，如 "protein"
      nutrient_name:        string;         // 营养素显示名称
      value:                number | null;  // 实际摄入值
      unit:                 string | null;  // 单位，如 "g"、"mg"、"IU"
      min_required:         number | null;  // AAFCO 最低需求
      max_allowed:          number | null;  // AAFCO 最高上限
      ideal_target:         number | null;  // 理想目标值
      meets_min:            boolean;        // 是否达到最低需求
      meets_max:            boolean;        // 是否未超过最高上限
      deviation_from_ideal: number | null;  // 偏离理想值的绝对差
    }>;
  }>;
}
```

**示例响应（简化）**：

```json
{
  "success": true,
  "total": 5,
  "elapsed_seconds": 87.3,
  "recipes": [
    {
      "rank": 1,
      "recipe_id": "abc-123",
      "total_weight_grams": 450.0,
      "objective_value": 123.4,
      "used_supplements": [],
      "weights": [
        {
          "ingredient_id": "uuid-xxx",
          "ingredient_name": "Chicken Breast",
          "weight_grams": 200.0,
          "percentage": 44.4,
          "is_supplement": false
        }
      ],
      "nutrient_analysis": [
        {
          "nutrient_id": "protein",
          "nutrient_name": "Protein",
          "value": 85.2,
          "unit": "g",
          "min_required": 70.0,
          "max_allowed": null,
          "ideal_target": null,
          "meets_min": true,
          "meets_max": true,
          "deviation_from_ideal": null
        },
        {
          "nutrient_id": "carbohydrate",
          "nutrient_name": "Carbohydrate",
          "value": 12.3,
          "unit": "g",
          "min_required": null,
          "max_allowed": null,
          "ideal_target": null,
          "meets_min": true,
          "meets_max": true,
          "deviation_from_ideal": null
        }
      ]
    }
  ]
}
```

---

#### 前端如何使用响应数据

```tsx
// useRecipeGeneration.ts
const response = await generateRecipes(request);

// 存入 sessionStorage，供 RecipeResult / RecipeDetail 页面读取
sessionStorage.setItem("recipe_results", JSON.stringify(response.recipes));

// 跳转到结果页
navigate("/recipes/result");
```

**RecipeResult.tsx**（列表页）读取方式：

```tsx
const raw = sessionStorage.getItem("recipe_results");
const recipes = JSON.parse(raw) as RecipeResult[];
// 从 nutrient_analysis 读宏量营养素
const nMap = Object.fromEntries(recipe.nutrient_analysis.map(n => [n.nutrient_id, n.value]));
const protein = nMap["protein"];
const fat     = nMap["fat"];
const carb    = nMap["carbohydrate"];
```

**RecipeDetail.tsx**（详情页）读取方式：

```tsx
const raw = sessionStorage.getItem("recipe_detail");
const recipe = JSON.parse(raw) as RecipeResult;
// 前端计算 % of min_required
const pct = (n.value / n.min_required) * 100;
// Ca:P 比值
const caP = nMap["calcium"].value / nMap["phosphorus"].value;
```

---

#### 错误响应

| HTTP 状态码 | 原因 |
| --- | --- |
| 422 | life_stage 不合法（不在 LifeStage 枚举中） |
| 503 | 服务正在初始化（启动期间） |
| 500 | 后端计算异常 |

---

---

### 3. GET /health — 健康检查

**URL**：`GET /health`

**响应**：

```json
{
  "status": "healthy",
  "ingredients_loaded": 1234
}
```

---

## L1 Interface

- **l1_generator = L1RecipeGenerator(ingredients_df)**
- **candidates = *self*.l1.generate(*pet*)**

```python
        Returns:
            List[RecipeCombination]
            
class RecipeCombination:
    """L1 输出的候选组合"""
    recipe_id: str
    ingredients: Dict[str, List[Ingredient]]  # slot_name -> [ingredients]
    
    # 评分指标
    diversity_score: float = 0.0
    risk_score: float = 0.0  # 风险分数(越低越好)
    completeness_score: float = 0.0  # 完整性分数
    
    # 元数据
    active_slots: List[str] = field(default_factory=list)
    applied_rules: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
```

## Enum

```python
@unique
class NutrientID(IntEnum):
    """
    营养素 ID 定义 (USDA 标准 ID)
    保持纯净，只做标识符
    """
    # === 基础 ===
    ENERGY           = 1008
    WATER            = 1051
    ASH              = 1007
    
    # === 宏量 ===
    PROTEIN          = 1003
    FAT              = 1004
    CARBOHYDRATE     = 1005
    FIBER            = 1079
    
    # === 氨基酸 ===
    ARGININE         = 1220
    HISTIDINE        = 1221
    ISOLEUCINE       = 1212
    LEUCINE          = 1213
    LYSINE           = 1214
    METHIONINE       = 1215
    CYSTINE          = 1216
    PHENYLALANINE    = 1217
    TYROSINE         = 1218
    THREONINE        = 1211
    TRYPTOPHAN       = 1210
    VALINE           = 1219
    
    # === 脂肪酸 ===
    LA               = 1269 # Linoleic 18:2 n-6
    ALA              = 1404 # Alpha-Linolenic 18:3 n-3
    ARA              = 1271 # Arachidonic 20:4
    EPA              = 1278
    DHA              = 1272
    
    # === 矿物质 ===
    CALCIUM          = 1087
    PHOSPHORUS       = 1091
    POTASSIUM        = 1092
    SODIUM           = 1093
    CHLORIDE         = 1088
    MAGNESIUM        = 1090
    IRON             = 1089
    COPPER           = 1098
    MANGANESE        = 1101
    ZINC             = 1095
    IODINE           = 1100
    SELENIUM         = 1103

    # === 维生素 ===
    VITAMIN_A        = 1104
    VITAMIN_D        = 1110
    VITAMIN_E        = 1109
    THIAMIN          = 1165
    RIBOFLAVIN       = 1166
    NIACIN           = 1167
    PANTOTHENIC_ACID = 1170
    PYRIDOXINE       = 1175
    VITAMIN_B12      = 1178
    FOLIC_ACID       = 1186
    CHOLINE          = 1180

```

```python
class Species(str, Enum):
    DOG = "dog"
    CAT = "cat"

class LifeStage(Enum):
    """生命阶段"""
    DOG_ADULT = "adult"
    DOG_PUPPY = "puppy"
    DOG_SENIOR = "senior"

    def to_aafco_standard(self):
        """映射回 AAFCO 标准"""
        if self == LifeStage.DOG_SENIOR:
            return LifeStage.DOG_ADULT
        return self

class ActivityLevel(str,Enum):
    SEDENTARY = "sedentary"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"

class SterilizationStatus(str, Enum):
    INTACT = "intact"
    NEUTERED = "neutered"

class ReproductiveStage(str, Enum):
    NONE = "none"
    PREGNANT = "pregnant"
    LACTATING = "lactating"
```

## Energy Calculator Interface

```sql
def calculate_resting_energy_requirement(weight_kg: float) -> float:

@dataclass
class EnergyCalculationResult:
    """能量计算结果"""
    resting_energy_kcal: float  # 静息能量需求（千卡/天），保留1位小数
    daily_energy_kcal: float    # 每日能量需求（千卡/天），保留1位小数
    life_stage: str             # 生命阶段（对应LifeStage枚举值）
    model_version: str          # 计算器版本号（如：EnergyCalculator-v0.2）
    calculation_breakdown: Dict[str, float]  # 计算过程分解，键为步骤名称，值为对应数值（保留2位小数）
    warnings: list[str]         # 警告信息列表（如参数异常、老年调整提示等）
    
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
    lactation_week: int = 4,
    nursing_count: int = 1,
    senior_month: int = 84,
    energy_requirement: float = None
) -> EnergyCalculationResult:
```

## L2 Interface

- L2Input

```python
@dataclass
class L2Input:
    """L2 引擎的完整输入"""
    pet: PetProfile
    combination: RecipeCombination
    supplement_toolkit: List[Ingredient]  # 可用的补剂列表

    nutrient_matrix: pd.DataFrame
    nutrient_info: pd.DataFrame
    nutrient_conversion_factor: Dict[int, float]  # 单位转换器
    converted_nutrient_matrix: pd.DataFrame  # 单位转换后的营养成分矩阵
```

- result = *self*.l2.**optimize**(**l2_input**) -> **OptimizationResult**
    - **_solve_phase**(self, L2Input, use_supplements: bool) -> **OptimizationResult**
        - **_parse_result** (self, status: int, l2_input: L2Input, ingredients: List[Ingredient], use_supplements: bool ) -> **OptimizationResult**
            - nutrient_analysis=**_analyze_nutrients**(    self,weights: List[OptimizedWeight], ingredients: List[Ingredient], pet: PetProfile, nutrition_matrix :pd.DataFrame, nutrient_sum_dict: Dict[int, float] ) -> **List[NutrientAnalysis]**

```python
        Returns:
            OptimizationResult
@dataclass
class OptimizationResult:
    """L2 优化结果"""
    # 求解状态
    status: SolveStatus
    solve_time_seconds: float
    
    # 如果成功
    weights: Optional[List[OptimizedWeight]] = None
    total_weight_grams: Optional[float] = None
    nutrient_analysis: Optional[List[NutrientAnalysis]] = None
    
    # 目标函数值
    objective_value: Optional[float] = None
    penalty_breakdown: Optional[Dict[str, float]] = None  # {toxic: x, balance: y, supplement: z}
    
    # 如果失败
    infeasibility_diagnostic: Optional[InfeasibilityDiagnostic] = None
    
    # 元数据
    recipe_id: str = ""
    used_supplements: List[str] = field(default_factory=list)
    
    @dataclass
		class OptimizedWeight:
		    """优化后的食材重量"""
		    ingredient_id: str
		    ingredient_name: str
		    weight_grams: float
		    is_supplement: bool = False
	    
		@dataclass
		class NutrientAnalysis:
		    """营养分析报告"""
		    nutrient_id: str
		    nutrient_name: str
		    value: float                    # 实际值
		    unit: str                       # 单位
		    
		    # 约束情况
		    min_required: Optional[float] = None
		    max_allowed: Optional[float] = None
		    ideal_target: Optional[float] = None
		    
		    # 达标情况
		    meets_min: bool = True
		    meets_max: bool = True
		    deviation_from_ideal: Optional[float] = None
```

# Database Interface

- **ingredients_df = IngredientDataLoader.load_ingredients_for_l1()**

```python
        Returns:
            DataFrame with columns:
            - ingredient_id (str/UUID)
            - description (str)
            - short_name (str)
            - food_group (str)
            - food_subgroup (str)
            - tags (List[str]) - 所有标签的列表
            - diversity_cluster (str)
            - is_active (bool)
```

- **nutrition_matrix, info_df = *self*.data_loader.get_nutrition_matrix_for_l2(all_unique_ids)**

```python
        Returns:
            (wide_matrix, nutrients_info)
            
            wide_matrix: 宽表格式
                index: ingredient_id
                columns: nutrient_id
                values: amount_per_100g
            
            nutrients_meta: 营养素信息
                columns: nutrient_id, name, unit_name, is_key
```