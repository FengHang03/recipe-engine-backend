"""
explain/models.py
All Pydantic data structures for the Recipe Explain middleware pipeline.
Schema version: 1.0

Pipeline flow:
  ExplainRecipeRequest
    → NormalizedExplainInput        (Layer 1: Normalizer)
    → EnrichedExplainInput          (Layer 2: Enrichment)
    → DerivedMetrics                (Layer 3: DerivedMetricsBuilder)
    → RuleEngineResult              (Layer 4: RuleEngine)
    → RecipeExplanationContext      (Layer 5: ContextBuilder)
    → RecipeExplanationOutput       (Layer 6: LLMService → frontend)
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, AliasChoices, ConfigDict

from app.shared.contracts.nutrition import NutrientAnalysis
from app.shared.contracts.pet import PetProfile
from app.domains.recipe_generation.contracts.results import RecipeGenerationResult


# ---------------------------------------------------------------------------
# Section 1 — API Input (from frontend)
# ---------------------------------------------------------------------------

class ExplainRecipeRequest(BaseModel):
    """
    Internal explain-layer request.

    Directly reuses the shared recipe-generation contracts so that
    explain input stays aligned with the actual generation output.
    """
    pet                             : PetProfile
    recipe                          : RecipeGenerationResult


# ---------------------------------------------------------------------------
# Section 2 — Layer 1: Normalizer output
# ---------------------------------------------------------------------------

class NormalizedPetContext(BaseModel):
    species                         : str       # unified lowercase "dog"
    life_stage                      : str       # unified uppercase "DOG_PUPPY"
    age_months                      : Optional[int] = None
    body_weight_kg                  : float                   # unified from weight_kg
    size_class                      : Optional[str] = None
    daily_calories_kcal             : float             # unified from daily_calories_kcal
    # kept in pipeline but not forwarded to LLM in MVP
    activity_level                  : Optional[str] = None
    sterilization_status            : Optional[str] = None
    reproductive_stage              : Optional[str] = None
    health_conditions               : List[str] = Field(default_factory=list)
    allergies                       : List[str] = Field(default_factory=list)


class NormalizedRecipeContext(BaseModel):
    recipe_id                       : str   # = recipe_id
    rank                            : Optional[int] = None
    total_weight_grams              : Optional[float] = None
    used_supplements                : List[str] = Field(default_factory=list)


class NormalizedIngredient(BaseModel):
    ingredient_id                   : str
    ingredient_name                 : str
    weight_grams                    : float
    pct_of_recipe                   : Optional[float] = None
    is_supplement                   : bool = False
    slot_type                       : Optional[str] = None
    display_amount_text             : Optional[str] = None


class NormalizedExplainInput(BaseModel):
    pet_context                     : NormalizedPetContext
    recipe_context                  : NormalizedRecipeContext
    ingredients                     : List[NormalizedIngredient]
    nutrient_analysis               : List[NutrientAnalysis]  # passed through, nutrient_id normalized


# ---------------------------------------------------------------------------
# Section 3 — Layer 2: Enrichment output
# ---------------------------------------------------------------------------

class EnrichedIngredient(BaseModel):
    ingredient_id: str
    ingredient_name: str
    weight_grams: float
    pct_of_recipe: Optional[float] = None
    is_supplement                   : bool = False
    slot_type: Optional[str] = None
    # fields populated from DB — ingredients table
    food_group: Optional[str] = None    # e.g. "organ_liver", "fruit_blue"
    food_subgroup: Optional[str] = None         # e.g. "organ_liver" — from DB ingredients table
    max_g_per_kg_bw: Optional[float] = None
    max_pct_kcal: Optional[float] = None       # reserved — not used this sprint
    # fields populated from DB — ingredient_tags table (ingredient_id, tag_type, tag)
    role_tags: List[str] = Field(default_factory=list)
    risk_tags: List[str] = Field(default_factory=list)
    note_tags: List[str] = Field(default_factory=list)
    # graceful degradation: False = DB lookup failed, downstream rules degrade safely
    enrich_available: bool = False
    # populated by DerivedMetricsBuilder (not available until Layer 3)
    grams_per_kg_bw: Optional[float] = None


class EnrichedExplainInput(BaseModel):
    normalized: NormalizedExplainInput
    enriched_ingredients: List[EnrichedIngredient]


# ---------------------------------------------------------------------------
# Section 4 — Layer 3: Derived metrics output
# ---------------------------------------------------------------------------

class CategoryTotal(BaseModel):
    category: str
    total_grams: float
    pct_of_recipe: Optional[float] = None


class StructureSnapshot(BaseModel):
    has_main_protein: bool = False
    has_calcium_source: bool = False
    has_omega3_support: bool = False
    has_carbohydrate_source: bool = False
    has_vegetable: bool = False
    has_liver: bool = False


class IngredientSummaryItem(BaseModel):
    """Compressed ingredient entry — used by ContextBuilder and forwarded to LLM."""
    ingredient_name: str
    pct_of_recipe: Optional[float] = None
    grams_per_kg_bw: float
    food_group: Optional[str] = None
    slot_type: Optional[str] = None
    risk_tags: List[str] = Field(default_factory=list)  # reserved â not used this sprint


class IngredientSummary(BaseModel):
    ingredients: List[IngredientSummaryItem]


class DerivedMetrics(BaseModel):
    ingredient_metrics: List[EnrichedIngredient]
    category_totals: List[CategoryTotal]
    structure_snapshot: StructureSnapshot
    supplement_count: int
    non_supplement_count: int
    total_ingredients_count: int
    ca_p_ratio: Optional[float] = None
    ingredient_summary: IngredientSummary   # pre-built for ContextBuilder


# ---------------------------------------------------------------------------
# Section 5 — Layer 4: Rule Engine output
# ---------------------------------------------------------------------------

# ── 5.1 Nutrition Summary ────────────────────────────────────────────────────

class Level1Finding(BaseModel):
    """
    Status of a key nutrient against AAFCO min/max.
    MVP level1 nutrients: protein, fat, calcium, phosphorus
    Note: omega3_support is handled via structure_snapshot (has_omega3_support),
    not as a strict AAFCO nutrient value. ca_p_ratio goes into ratio_findings.
    """
    nutrient_id: str                        # internal — excluded from LLM prompt
    display_name: str                       # e.g. "Protein"
    category: str                           # "macro" | "mineral" | "vitamin"
    status: str                             # "strong" | "adequate" | "low" | "high"
    priority: str                           # "high" | "medium" | "low"
    value: Optional[float] = None
    unit: Optional[str] = None
    min_required: Optional[float] = None
    evidence_code: str = ""                 # internal — excluded from LLM prompt


class FlaggedNutrient(BaseModel):
    """Nutrient that failed meets_min or exceeded max_allowed."""
    nutrient_id: str                        # internal — excluded from LLM prompt
    display_name: str
    category: str
    status: str                             # "low" | "high" | "missing"
    severity: str                           # "high" | "medium"
    priority: str
    value: Optional[float] = None
    unit: Optional[str] = None
    min_required: Optional[float] = None
    max_allowed: Optional[float] = None
    reason_code: str = ""                   # internal — excluded from LLM prompt


class RatioFinding(BaseModel):
    """
    Ca:P ratio assessment.
    Value sourced from DerivedMetrics.ca_p_ratio, not nutrient_analysis directly.
    """
    ratio_id: str                           # e.g. "ca_p_ratio"
    display_name: str                       # e.g. "Ca:P Ratio"
    status: str                             # "normal" | "borderline" | "abnormal"
    severity: str                           # "high" | "medium"
    priority: str
    value: Optional[float] = None
    min_target: Optional[float] = None
    max_target: Optional[float] = None
    reason_code: str = ""                   # internal — excluded from LLM prompt


class NutritionSummary(BaseModel):
    model_config = ConfigDict(extra='forbid')

    level1_findings: List[Level1Finding] = Field(default_factory=list)
    flagged_nutrients: List[FlaggedNutrient] = Field(default_factory=list)
    ratio_findings: List[RatioFinding] = Field(default_factory=list)
    # level2_triggered_findings: reserved for future sprint


# ── 5.2 Formula Review ───────────────────────────────────────────────────────

class FormulaReview(BaseModel):
    model_config = ConfigDict(extra='forbid')

    sanity_status: str                      # "reasonable" | "needs_adjustment" | "questionable"
    key_concerns: List[str] = Field(default_factory=list)
    # key_concerns: rule-confirmed problem summaries, forwarded to LLM and fallback
    # e.g. "Calcium appears below target"
    # e.g. "Ca:P ratio is below the preferred range"
    # e.g. "Fruit proportion may be high for a small puppy"


# ── 5.3 Flags ────────────────────────────────────────────────────────────────

class StrengthFlag(BaseModel):
    """
    Codes:
      strong_protein_support | balanced_ca_p_ratio |
      clear_calcium_source_present | limited_supplement_dependency
    """
    model_config = ConfigDict(extra='forbid')

    type: str                               # "nutritional" | "formula_structure"
    code: str
    priority: str                           # "high" | "medium" | "low"


class RiskFlag(BaseModel):
    """
    Codes:
      ca_p_ratio_below_target | ca_p_ratio_above_target |
      missing_calcium_source | missing_omega3_support |
      high_fruit_for_small_puppy | high_liver_proportion |
      ingredient_exceeds_g_per_kg_bw_limit | high_supplement_dependency
    """
    model_config = ConfigDict(extra='forbid')

    type: str                               # "ratio_imbalance" | "formula_structure"
                                            # | "ingredient_amount"
    severity: str                           # "high" | "medium"
    code: str
    priority: int                           # lower number = higher priority
    recommended_action_code: Optional[str] = None   # internal — drives fallback text


class FeedingGuidanceFlag(BaseModel):
    """
    Codes:
      split_into_3_meals_for_small_puppy | watch_stool_quality |
      monitor_body_weight_and_condition | increase_calcium_support |
      rebalance_calcium_phosphorus | add_omega3_support | reduce_fruit_proportion
    """
    model_config = ConfigDict(extra='forbid')

    type: str                               # "feeding_strategy" | "monitoring" | "adjustment"
    code: str
    priority: str                           # "high" | "medium" | "low"
    human_readable: Optional[str] = None    # populated from CODE_TO_READABLE in guidance_rules


# ── 5.4 Ingredient Adjustment Ideas — reserved, NOT implemented this sprint ──

class IngredientAdjustmentIdea(BaseModel):
    """
    Reserved interface — NOT populated in MVP sprint.
    Next sprint activation plan:
      - Add RecipeExplanationContext.improvement_suggestions: List[IngredientAdjustmentIdea]
      - Populate RecipeExplanationOutput.ingredient_adjustment_ideas from LLM output
    """
    kind: str                               # "addition" | "replacement"
    reason_code: str
    candidates: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    priority: Optional[str] = None


# ── 5.5 Rule Engine Result ───────────────────────────────────────────────────

class RuleEngineResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    nutrition_summary: NutritionSummary
    formula_review: FormulaReview
    strength_flags: List[StrengthFlag] = Field(default_factory=list)
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    feeding_guidance_flags: List[FeedingGuidanceFlag] = Field(default_factory=list)
    # reserved — added next sprint
    ingredient_adjustment_ideas: Optional[List[IngredientAdjustmentIdea]] = None


# ---------------------------------------------------------------------------
# Section 6 — Layer 5: Context passed to LLMService
#
# Uses the same internal types directly — no LLM* wrapper classes needed.
# Field trimming and internal-field exclusion is handled inside
# LLMService.build_user_prompt() in two passes:
#   Pass 1 (global): exclude nutrient_id, evidence_code, reason_code, ratio_id
#   Pass 2 (per-module): trim list lengths, filter category_totals by key categories
# ---------------------------------------------------------------------------

class ExplanationPolicy(BaseModel):
    tone: str = "professional_friendly"
    language: str = "en"                    # reserved for i18n
    max_strengths: int = 3
    max_risks: int = 4
    max_guidance_items: int = 4
    no_medical_claims: bool = True
    rule_engine_is_source_of_truth: bool = True


class RecipeExplanationContext(BaseModel):
    model_config = ConfigDict(extra='forbid')

    pet_context: NormalizedPetContext
    recipe_context: NormalizedRecipeContext
    nutrition_summary: NutritionSummary
    ingredient_summary: IngredientSummary
    category_totals: List[CategoryTotal] = Field(default_factory=list)
    structure_snapshot: StructureSnapshot = Field(default_factory=StructureSnapshot)
    formula_review: FormulaReview
    strength_flags: List[StrengthFlag] = Field(default_factory=list)
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    feeding_guidance_flags: List[FeedingGuidanceFlag] = Field(default_factory=list)
    # improvement_suggestions: reserved — added next sprint
    explanation_policy: ExplanationPolicy


# ---------------------------------------------------------------------------
# Section 7 — Layer 6: API Output (returned to frontend)
# ---------------------------------------------------------------------------

class OverviewOutput(BaseModel):
    status: str                             # mirrors sanity_status
    headline: str                           # one-line LLM-generated title
    summary: str                            # 2-3 sentence LLM-generated assessment
    confidence: Optional[str] = None        # "high" | "medium" | "low"


class KeyFindingOutput(BaseModel):
    title: str
    status: str                             # mirrors nutrient/ratio status
    importance: str                         # "high" | "medium" | "low"
    message: str


class NutritionInterpretationOutput(BaseModel):
    overall_assessment: str                 # LLM-generated paragraph
    key_findings: List[KeyFindingOutput] = Field(default_factory=list)


class StrengthOutput(BaseModel):
    title: str
    summary: str
    why_it_matters: Optional[str] = None


class RiskOutput(BaseModel):
    severity: str                           # "high" | "medium"
    title: str
    summary: str
    why_it_matters: Optional[str] = None
    suggested_fix: Optional[str] = None


class GuidanceTextItem(BaseModel):
    text: str


class FeedingGuidanceOutput(BaseModel):
    feeding_strategy: List[GuidanceTextItem] = Field(default_factory=list)
    monitoring_points: List[GuidanceTextItem] = Field(default_factory=list)
    adjustments_to_consider: List[GuidanceTextItem] = Field(default_factory=list)


class PlainLanguageTakeaway(BaseModel):
    for_pet_parent: str                     # LLM-generated plain-language summary


class IngredientAdjustmentIdeasOutput(BaseModel):
    """Reserved — always empty in MVP sprint."""
    additions: List[dict] = Field(default_factory=list)
    replacements: List[dict] = Field(default_factory=list)


class MetaOutput(BaseModel):
    confidence: str                         # "high" | "medium" | "low"
    generated_from: str = "rule_grounded_llm"
    fallback_used: bool = False


class RecipeExplanationOutput(BaseModel):
    schema_version: str = "1.0"
    recipe_id: str
    overview: OverviewOutput
    playful_comment: Optional[str] = None
    nutrition_interpretation: NutritionInterpretationOutput
    strengths: List[StrengthOutput] = Field(default_factory=list)
    risks: List[RiskOutput] = Field(default_factory=list)
    feeding_guidance: FeedingGuidanceOutput
    plain_language_takeaway: PlainLanguageTakeaway
    ingredient_adjustment_ideas: IngredientAdjustmentIdeasOutput = Field(
        default_factory=IngredientAdjustmentIdeasOutput
    )                                       # reserved, always empty this sprint
    meta: MetaOutput
