# Frontend Interface

- **PetProfile**

```python
@dataclass
class PetProfile:
    """宠物画像"""
    target_calories: float          # 目标热量 (kcal/day)
    body_weight: float              # 体重 (kg)
    life_stage: LifeStage           # 生命阶段
    
    # 可选字段
    allergies: List[str] = field(default_factory=list)
    size_class: Optional[str] = "medium"
    activity_level: Optional[str] = None
    health_conditions: List[str] = field(default_factory=list)
    reproductive_status:Optional[ReproductiveStatus] = 'intact'
    repro_status: Optional[ReproState] = None
```

# Database Interface

- **ingredients_df = IngredientDataLoader.load_ingredients_for_l1()**

```python
        Returns:
            DataFrame with columns:
            - ingredient_id (str/UUID)
            - description (str)
            - short_name (str)
            - ingredient_group (str)
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

# L1 Interface

- **l1_generator = L1RecipeGenerator(ingredients_df)**
- **candidates = *self*.l1.generate(*pet_profile*)**

```python
        Returns:
            List[RecipeCombination]
            
class RecipeCombination:
    """L1 输出的候选组合"""
    combination_id: str
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

# L2 Interface

- L2Input

```python
@dataclass
class L2Input:
    """L2 引擎的完整输入"""
    pet_profile: PetProfile
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
            - nutrient_analysis=**_analyze_nutrients**(    self,weights: List[OptimizedWeight], ingredients: List[Ingredient], pet_profile: PetProfile, nutrition_matrix :pd.DataFrame, nutrient_sum_dict: Dict[int, float] ) -> **List[NutrientAnalysis]**

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
    combination_id: str = ""
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

# Energy Calculator Interface

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
    reproductive_status: ReproductiveStatus,
    repro_state: ReproState,
    breed: Optional[str] = None,
    lactation_week: int = 4,
    nursing_count: int = 1,
    senior_month: int = 84,
    energy_requirement: float = None
) -> EnergyCalculationResult:
```

# Enum

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

class ReproductiveStatus(str, Enum):
    INTACT = "intact"
    NEUTERED = "neutered"

class ReproState(str, Enum):
    NONE = "none"
    PREGNANT = "pregnant"
    LACTATING = "lactating"
```