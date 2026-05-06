"""
recipe_generation/contracts/enums
"""
from enum import Enum, IntEnum, unique

# ==================== 枚举定义 ====================

class SolveStatus(str, Enum):
    OPTIMAL     = "OPTIMAL"
    FEASIBLE    = "FEASIBLE"
    INFEASIBLE  = "INFEASIBLE"
    TIMEOUT     = "TIMEOUT"
    ERROR       = "ERROR"


class InfeasibilityReason(str, Enum):
    """Infeasibility Reason"""
    NUTRIENT_DEFICIT    = "nutrient_deficit"        # 营养素不足 (Code 1001)
    TOXIC_CONFLICT      = "toxic_conflict"          # 毒性冲突 (Code 1002)
    RATIO_CONFLICT      = "ratio_conflict"          # 比率冲突 (Code 1003)
    SLOT_CONFLICT       = "slot_conflict"           # 槽位冲突
    UNKNOWN             = "unknown"


class RecipeGenerationMode(str, Enum):
    """Recipe Generation Mode"""
    OPTIMIZE_FIXED_SET      = "optimize_fixed_set"
    OPTIMIZE_USER_DEFINED   = "optimize_user_defined"
    SCALE_PRESET            = "scale_preset"
    BEGINNER_DIY_PREVIEW    = "beginner_diy_preview"
    PRESET_WITH_TOLERANCE   = "preset_with_tolerance"


class MacroPreference(str, Enum):
    STANDARD    = "standard"
    HIGH        = "high"
    LOW         = "low"
