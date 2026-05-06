"""

"""

from typing import Any, List, Dict, Literal, Optional
from pydantic import BaseModel, Field, model_validator

from app.shared.contracts.enums import(
    SlotType
)
from app.shared.contracts.ingredient import IngredientRef, IngredientProfile


# ---------------------------------------------------------------------------
# Existing spec: combination / manual / DIY
# ---------------------------------------------------------------------------

class RecipeCombinationSpec(BaseModel):
    recipe_id               : str
    ingredients             : Dict[SlotType, List[IngredientRef]] = Field(default_factory=dict) # slot_name -> [ingredients]

    diversity_score         : float = 0.0
    risk_score              : float = 0.0
    completeness_score      : float = 0.0

    n_core_ingredients      : int = 0
    n_fat_oil               : int = 0
    n_supplement            : int = 0
    n_total_items           : int = 0

    active_slots            : List[SlotType] = Field(default_factory=list)
    applied_rules           : List[str] = Field(default_factory=list)
    metadata                : Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, /, **data: Any) -> None:
        super().__init__(**data)
    
    def get_all_ingredients(self) -> List[IngredientRef]:
        """获取所有食材"""
        result = []
        for ing_list in self.ingredients.values():
            result.extend(ing_list)
        return result
    
    def calculate_ingredient_stats(self):
        """
        计算食材分类统计
        
        分类：
        - 核心食材: 不包括 FAT_OIL 和 SUPPLEMENT
        - FAT_OIL: 食用油
        - SUPPLEMENT: 补充剂
        """
        self.n_core_ingredients = 0
        self.n_fat_oil = 0
        self.n_supplement = 0
        self.n_total_items = 0
        
        for ing in self.get_all_ingredients():
            self.n_total_items += 1
            
            if ing.food_group == "FAT_OIL":
                self.n_fat_oil += 1
            elif ing.food_group == "SUPPLEMENT":
                self.n_supplement += 1
            else:
                self.n_core_ingredients += 1

    def get_ingredient_ids(self) -> List[str]:
        """获取所有食材ID"""
        return [ing.ingredient_id for ing in self.get_all_ingredients()]


class UserSelectedIngredient(BaseModel):
    ingredient                      : IngredientRef
    slot_type                       : Optional[SlotType] = None

    is_locked                       : bool = False
    is_optional                     : bool = False

    min_weight_g                    : Optional[float] = None
    max_weight_g                    : Optional[float] = None

    target_ratio                    : Optional[float] = None
    min_ratio                       : Optional[float] = None
    max_ratio                       : Optional[float] = None


class UserDefinedRecipeSpec(BaseModel):
    recipe_id                       : str
    ingredients                     : List[UserSelectedIngredient] = Field(default_factory=list) # UserSelectedIngredient # slot_name -> [ingredients]

    notes                           : Optional[str] = None
    metadata                        : Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Preset recipe: anchors / dosing / resolved states
# ---------------------------------------------------------------------------

class PresetRecipeItem(BaseModel):
    """
    This object serves two states simultaneously:

    A. Original Definition State (after repository/mapper input)
       - weight_curve
       - dose_tiers
       - base_weight_g / base_ratio
       - grams_per_unit / default_unit

    B. Current Pet Resolved State (after resolve_full_preset_spec)
       - resolved_weight_g
       - resolution_mode
       - resolved_unit

    Conventions:
    - Frontend display / RecipeGenerationResult.weight_grams uses resolved_weight_g (raw grams)
    - Perform internal raw -> cooked conversion before nutrient analysis
    """
    ingredient                  : IngredientRef
    slot_type                   : SlotType

    # 兼容旧逻辑 / fallback
    base_weight_g               : Optional[float] = None
    base_ratio                  : Optional[float] = None

    # supplement 单位信息
    default_unit                : Optional[Literal["g", "tsp", "cap", "tab"]] = None
    grams_per_unit              : Optional[float] = None

    # 通用标记
    is_optional                 : bool = False
    notes                       : Optional[str] = None

    # --------------------------
    # 当前宠物解析后的字段
    # --------------------------
    resolved_weight_g           : Optional[float] = None
    resolved_unit               : Optional[Literal["g", "tsp", "cap", "tab"]] = None
    resolution_mode             : Optional[str] = None
    resolution_note             : Optional[str] = None

    @property
    def is_resolved(self) -> bool:
        return self.resolved_weight_g is not None

    @model_validator(mode="after")
    def validate_item(self) -> "PresetRecipeItem":
        if self.resolved_weight_g is not None and self.resolved_weight_g < 0:
            raise ValueError("PresetRecipeItem.resolved_weight_g must be >= 0")

        return self


class PresetRecipeSpec(BaseModel):
    """
    Unified runtime specification for preset recipes.

    In the repository/mapper phase:
    - ingredients may retain weight_curve / dose_tiers
    - resolved_weight_g is not populated

    After resolve_full_preset_spec:
    - ingredients[*].resolved_weight_g is fully populated
    - Subsequent scalers only read resolved_weight_g to generate WeightedIngredient
    """
    recipe_id: str
    name: str
    description: Optional[str] = None

    ingredients: List[PresetRecipeItem] = Field(default_factory=list)

    basis_kcal: Optional[float] = None
    basis_total_weight_g: Optional[float] = None

    display_basis: Literal["raw"] = "raw"
    analysis_basis: Literal["raw", "mixed_cooked"] = "mixed_cooked"
    weight_resolution_mode: str = "interpolate_by_pet_weight"

    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def resolved_items(self) -> List[PresetRecipeItem]:
        return [item for item in self.ingredients if item.resolved_weight_g is not None]

    @property
    def unresolved_items(self) -> List[PresetRecipeItem]:
        return [item for item in self.ingredients if item.resolved_weight_g is None]

    def get_ingredient_ids(self) -> List[str]:
        return [item.ingredient.ingredient_id for item in self.ingredients]

    def is_fully_resolved(self) -> bool:
        if not self.ingredients:
            return False
        return all(item.resolved_weight_g is not None for item in self.ingredients)

    @model_validator(mode="after")
    def validate_spec(self) -> "PresetRecipeSpec":
        if not self.recipe_id:
            raise ValueError("PresetRecipeSpec.recipe_id is required")
        if not self.name:
            raise ValueError("PresetRecipeSpec.name is required")
        if not self.ingredients:
            raise ValueError("PresetRecipeSpec.ingredients must not be empty")
        return self


class PresetRecipeRef(BaseModel):
    recipe_id: str

# ---------------------------------------------------------------------------
# Beginner DIY
# ---------------------------------------------------------------------------

class BeginnerCategoryIngredientSpec(BaseModel):
    ingredient                      : IngredientRef
    internal_ratio                  : float  # 分类内占比，0~100


class BeginnerCategorySpec(BaseModel):
    category_key                    : str
    category_ratio                  : float  # 分类总占比，0~100
    is_active                       : bool = True
    ingredients                     : List[BeginnerCategoryIngredientSpec] = Field(default_factory=list)


class BeginnerSupplementSpec(BaseModel):
    ingredient                      : IngredientRef
    grams                           : float


class BeginnerDiyRecipeSpec(BaseModel):
    recipe_id                       : str

    target_energy_kcal              : Optional[float] = None

    categories                      : List[BeginnerCategorySpec] = Field(default_factory=list)
    supplements                     : List[BeginnerSupplementSpec] = Field(default_factory=list)

    notes                           : Optional[str] = None
    display_context                 : Dict[str, Any] = Field(default_factory=dict)
    metadata                        : Dict[str, Any] = Field(default_factory=dict)


class PresetRecipeRef(BaseModel):
    """
    Lightweight request-time reference used by frontend / orchestration.
    Only identifies which preset recipe to load.
    """
    recipe_id: str


class WeightAnchorPoint(BaseModel):
    """
    Raw preset weight interpolation anchor for core foods.
    """
    weight_kg: float
    ingredient_weight_g: float

    @model_validator(mode="after")
    def validate_anchor(self) -> "WeightAnchorPoint":
        if self.weight_kg <= 0:
            raise ValueError("WeightAnchorPoint.weight_kg must be > 0")
        if self.ingredient_weight_g < 0:
            raise ValueError("WeightAnchorPoint.ingredient_weight_g must be >= 0")
        return self


class DoseTier(BaseModel):
    """
    Weight-based supplement dosage tier.
    """
    min_weight_kg: float
    max_weight_kg: float
    amount: float
    unit: Literal["g", "tsp", "cap", "tab"]

    @model_validator(mode="after")
    def validate_tier(self) -> "DoseTier":
        if self.min_weight_kg <= 0:
            raise ValueError("DoseTier.min_weight_kg must be > 0")
        if self.max_weight_kg < self.min_weight_kg:
            raise ValueError("DoseTier.max_weight_kg must be >= min_weight_kg")
        if self.amount < 0:
            raise ValueError("DoseTier.amount must be >= 0")
        return self


class RawPresetRecipeItem(BaseModel):
    """
    Raw preset definition item loaded from infra.data / repository.

    This is NOT the runtime resolved spec item.
    It still carries weight_curve / dose_tiers.
    """
    fdc_id: str
    slot_type: SlotType

    # core-food resolution
    weight_curve: List[WeightAnchorPoint] = Field(default_factory=list)

    # supplement resolution
    dose_tiers: List[DoseTier] = Field(default_factory=list)

    # fallback / legacy support
    base_weight_g: Optional[float] = None
    base_ratio: Optional[float] = None

    # supplement unit conversion
    default_unit: Optional[Literal["g", "tsp", "cap", "tab"]] = None
    grams_per_unit: Optional[float] = None

    # generic metadata
    is_optional: bool = False
    notes: Optional[str] = None

    @property
    def has_weight_curve(self) -> bool:
        return len(self.weight_curve) > 0

    @property
    def has_dose_tiers(self) -> bool:
        return len(self.dose_tiers) > 0

    @model_validator(mode="after")
    def validate_item(self) -> "RawPresetRecipeItem":
        if not self.fdc_id or not str(self.fdc_id).strip():
            raise ValueError("RawPresetRecipeItem.fdc_id is required")

        if self.base_weight_g is not None and self.base_weight_g < 0:
            raise ValueError("RawPresetRecipeItem.base_weight_g must be >= 0")

        if self.base_ratio is not None and self.base_ratio < 0:
            raise ValueError("RawPresetRecipeItem.base_ratio must be >= 0")

        if self.grams_per_unit is not None and self.grams_per_unit <= 0:
            raise ValueError("RawPresetRecipeItem.grams_per_unit must be > 0")

        if self.has_dose_tiers:
            non_gram_units = [tier.unit for tier in self.dose_tiers if tier.unit != "g"]
            if non_gram_units and self.grams_per_unit is None:
                raise ValueError(
                    "RawPresetRecipeItem with non-gram dose_tiers must define grams_per_unit"
                )

        has_any_resolution_source = any([
            self.has_weight_curve,
            self.has_dose_tiers,
            self.base_weight_g is not None,
            self.base_ratio is not None,
        ])
        if not has_any_resolution_source:
            raise ValueError(
                "RawPresetRecipeItem must define at least one of: "
                "weight_curve, dose_tiers, base_weight_g, base_ratio"
            )

        return self


class RawPresetRecipeSpec(BaseModel):
    """
    Raw preset definition loaded from repository.
    Still carries all preset definition fields.
    """
    recipe_id: str
    name: str
    description: Optional[str] = None

    ingredients: List[RawPresetRecipeItem] = Field(default_factory=list)

    basis_kcal: Optional[float] = None
    basis_total_weight_g: Optional[float] = None

    display_basis: Literal["raw"] = "raw"
    analysis_basis: Literal["raw", "mixed_cooked"] = "mixed_cooked"
    weight_resolution_mode: str = "interpolate_by_pet_weight"

    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_spec(self) -> "RawPresetRecipeSpec":
        if not self.recipe_id:
            raise ValueError("RawPresetRecipeSpec.recipe_id is required")
        if not self.name:
            raise ValueError("RawPresetRecipeSpec.name is required")
        if not self.ingredients:
            raise ValueError("RawPresetRecipeSpec.ingredients must not be empty")
        return self

