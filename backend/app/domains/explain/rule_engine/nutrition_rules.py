"""
explain/rule_engine/nutrition_rules.py

Nutrition judgment — produces NutritionSummary, nutritional StrengthFlags,
and ratio-based RiskFlags.

MVP level1 nutrients  : protein, fat, calcium, phosphorus
ca_p_ratio            : ratio_findings  (sourced from DerivedMetrics.ca_p_ratio)
omega3_support        : NOT handled here — see structure_rules.py
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from app.domains.explain.contracts.contracts import (
    DerivedMetrics,
    FlaggedNutrient,
    Level1Finding,
    NutritionSummary,
    RatioFinding,
    RiskFlag,
    StrengthFlag,
)
from app.shared.contracts.enums import NutrientID
from app.shared.contracts.nutrition import NutrientAnalysis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Level1 nutrient definitions (MVP)
# ---------------------------------------------------------------------------

# (nutrient_id, display_name, category)
_LEVEL1_NUTRIENTS = [
    (NutrientID.PROTEIN, "Protein", "macro"),
    (NutrientID.FAT, "Fat", "macro"),
    (NutrientID.CALCIUM, "Calcium", "mineral"),
    (NutrientID.PHOSPHORUS, "Phosphorus", "mineral"),
]

# Ca:P target range
_CA_P_MIN = 1.0
_CA_P_MAX = 2.0
_CA_P_BORDERLINE_LOW  = 0.8   # [0.8, 1.0) → borderline
_CA_P_BORDERLINE_HIGH = 2.5   # (2.0, 2.5] → borderline
# below 0.8 or above 2.5 → abnormal

# Threshold for "strong" status: value >= min_required * this factor
_STRONG_THRESHOLD = 1.2

# Deviation threshold for severity split
_HIGH_SEVERITY_DEVIATION = 0.30  # > 30% deviation from min_required → "high"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    nutrient_analysis: List[NutrientAnalysis],
    derived: DerivedMetrics,
) -> Tuple[NutritionSummary, List[StrengthFlag], List[RiskFlag]]:
    """
    Returns:
      NutritionSummary   — level1_findings, flagged_nutrients, ratio_findings
      List[StrengthFlag] — strong_protein_support, balanced_ca_p_ratio
      List[RiskFlag]     — ca_p_ratio_below/above_target,
                           low_calcium, low_phosphorus, low_protein, low_fat
    """
    nutrient_map = {n.nutrient_id: n for n in nutrient_analysis}

    level1_findings, flagged_nutrients = _evaluate_level1(nutrient_map)
    ratio_findings, ratio_strengths, ratio_risks = _evaluate_ca_p_ratio(derived.ca_p_ratio)
    protein_strengths = _evaluate_protein_strength(level1_findings)
    deficiency_risks  = _evaluate_deficiency_risks(flagged_nutrients)

    nutrition_summary = NutritionSummary(
        level1_findings=level1_findings,
        flagged_nutrients=flagged_nutrients,
        ratio_findings=ratio_findings,
    )
    strength_flags = protein_strengths + ratio_strengths
    risk_flags     = ratio_risks + deficiency_risks

    return nutrition_summary, strength_flags, risk_flags


# ---------------------------------------------------------------------------
# Level1 evaluation
# ---------------------------------------------------------------------------

def _evaluate_level1(
    nutrient_map: dict[str, NutrientAnalysis],
) -> Tuple[List[Level1Finding], List[FlaggedNutrient]]:
    findings: List[Level1Finding] = []
    flagged:  List[FlaggedNutrient] = []

    for nutrient_id, display_name, category in _LEVEL1_NUTRIENTS:
        n = nutrient_map.get(nutrient_id)
        if n is None:
            logger.debug("Level1 nutrient %r not found in nutrient_analysis — skipped", nutrient_id)
            continue

        if n.value is None:
            logger.debug("Level1 nutrient %r has value=None — skipped", nutrient_id)
            continue

        status, priority, evidence_code = _classify_nutrient(n)

        findings.append(
            Level1Finding(
                nutrient_id=nutrient_id,
                display_name=display_name,
                category=category,
                status=status,
                priority=priority,
                value=n.value,
                unit=n.unit,
                min_required=n.min_required,
                evidence_code=evidence_code,
            )
        )

        if status in ("low", "high"):
            flagged.append(
                _build_flagged_nutrient(n, nutrient_id, display_name, category, status)
            )

    return findings, flagged


def _classify_nutrient(
    n: NutrientAnalysis,
) -> Tuple[str, str, str]:
    """Returns (status, priority, evidence_code)."""
    value = n.value  # already confirmed not None by caller

    # Check exceeded max first (takes priority over low check)
    if n.max_allowed is not None and value > n.max_allowed:
        return "high", "high", "above_maximum"

    if n.min_required is not None:
        if value >= n.min_required * _STRONG_THRESHOLD:
            return "strong", "high", "above_minimum_strong"
        if value >= n.min_required:
            return "adequate", "medium", "meets_minimum"
        return "low", "high", "below_minimum"

    # No min_required defined — report as adequate
    return "adequate", "low", "no_minimum_defined"


def _build_flagged_nutrient(
    n: NutrientAnalysis,
    nutrient_id: str,
    display_name: str,
    category: str,
    status: str,          # "low" | "high"
) -> FlaggedNutrient:
    severity = _deviation_severity(n)
    return FlaggedNutrient(
        nutrient_id=nutrient_id,
        display_name=display_name,
        category=category,
        status=status,
        severity=severity,
        priority="high" if severity == "high" else "medium",
        value=n.value,
        unit=n.unit,
        min_required=n.min_required,
        max_allowed=n.max_allowed,
        reason_code=f"{status}_{'min' if status == 'low' else 'max'}",
    )


def _deviation_severity(n: NutrientAnalysis) -> str:
    """
    Deviation > 30% from min_required → "high"; otherwise "medium".
    Falls back to "medium" when min_required is unavailable.
    """
    if n.min_required and n.min_required > 0 and n.value is not None:
        deviation = abs(n.value - n.min_required) / n.min_required
        return "high" if deviation > _HIGH_SEVERITY_DEVIATION else "medium"
    return "medium"



# ---------------------------------------------------------------------------
# Deficiency risk flag mapping
# Nutrients whose low status should also surface as a user-facing RiskFlag.
# nutrient_id → (risk_code, priority)
# ---------------------------------------------------------------------------

_DEFICIENCY_RISK_MAP: dict[str, tuple[str, int]] = {
    "calcium":    ("low_calcium",    1),   # highest priority — bone development
    "phosphorus": ("low_phosphorus", 2),
    "protein":    ("low_protein",    2),
    "fat":        ("low_fat",        3),
}


def _evaluate_deficiency_risks(
    flagged_nutrients: List[FlaggedNutrient],
) -> List[RiskFlag]:
    """
    Map flagged deficiency nutrients to user-facing RiskFlags.
    Only "low" status produces a deficiency risk (not "high" / excess).
    Priority and severity mirror the FlaggedNutrient.
    """
    risks: List[RiskFlag] = []
    for fn in flagged_nutrients:
        if fn.status != "low":
            continue
        mapping = _DEFICIENCY_RISK_MAP.get(fn.nutrient_id)
        if mapping is None:
            continue
        code, priority = mapping
        risks.append(RiskFlag(
            type="nutrient_deficiency",
            severity=fn.severity,
            code=code,
            priority=priority,
            recommended_action_code=None,
        ))
    return risks


# ---------------------------------------------------------------------------
# Ca:P ratio evaluation
# ---------------------------------------------------------------------------

def _evaluate_ca_p_ratio(
    ca_p_ratio: Optional[float],
) -> Tuple[List[RatioFinding], List[StrengthFlag], List[RiskFlag]]:
    if ca_p_ratio is None:
        return [], [], []

    status, severity, direction = _classify_ca_p(ca_p_ratio)

    finding = RatioFinding(
        ratio_id="ca_p_ratio",
        display_name="Ca:P Ratio",
        status=status,
        severity=severity,
        priority="high" if severity == "high" else "medium",
        value=ca_p_ratio,
        min_target=_CA_P_MIN,
        max_target=_CA_P_MAX,
        reason_code=f"ca_p_{status}_{direction}" if direction else f"ca_p_{status}",
    )

    strengths: List[StrengthFlag] = []
    risks:     List[RiskFlag]     = []

    if status == "normal":
        strengths.append(
            StrengthFlag(
                type="nutritional",
                code="balanced_ca_p_ratio",
                priority="medium",
            )
        )
    else:
        # borderline or abnormal → risk flag
        code = (
            "ca_p_ratio_below_target"
            if direction == "below"
            else "ca_p_ratio_above_target"
        )
        risks.append(
            RiskFlag(
                type="ratio_imbalance",
                severity=severity,
                code=code,
                priority=1 if severity == "high" else 2,
                recommended_action_code="rebalance_calcium_phosphorus",
            )
        )

    return [finding], strengths, risks


def _classify_ca_p(ratio: float) -> Tuple[str, str, str]:
    """
    Returns (status, severity, direction).
    direction: "below" | "above" | "" (normal)

    Thresholds:
      ratio < 0.8          → abnormal,   high,   below
      0.8 ≤ ratio < 1.0   → borderline, medium, below
      1.0 ≤ ratio ≤ 2.0   → normal,     medium, ""
      2.0 < ratio ≤ 2.5   → borderline, medium, above
      ratio > 2.5          → abnormal,   high,   above
    """
    if ratio < _CA_P_BORDERLINE_LOW:
        return "abnormal", "high", "below"
    if ratio < _CA_P_MIN:
        return "borderline", "medium", "below"
    if ratio <= _CA_P_MAX:
        return "normal", "medium", ""
    if ratio <= _CA_P_BORDERLINE_HIGH:
        return "borderline", "medium", "above"
    return "abnormal", "high", "above"


# ---------------------------------------------------------------------------
# Protein strength flag
# ---------------------------------------------------------------------------

def _evaluate_protein_strength(
    level1_findings: List[Level1Finding],
) -> List[StrengthFlag]:
    for f in level1_findings:
        if f.nutrient_id == "protein" and f.status == "strong":
            return [
                StrengthFlag(
                    type="nutritional",
                    code="strong_protein_support",
                    priority="high",
                )
            ]
    return []
