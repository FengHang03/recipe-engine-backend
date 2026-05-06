"""
explain/rule_engine/structure_rules.py

Structure judgment — evaluates StructureSnapshot and supplement counts
to produce structural StrengthFlags and RiskFlags.

Also handles omega3_support risk flag (omega3 is a structural signal,
not a strict AAFCO nutrient value).
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from app.domains.explain.contracts.contracts import (
    DerivedMetrics,
    RiskFlag,
    StrengthFlag,
    StructureSnapshot,
)

logger = logging.getLogger(__name__)

# Thresholds
_SUPPLEMENT_HIGH_THRESHOLD = 5   # supplement_count >= 5 → high_supplement_dependency
_SUPPLEMENT_LOW_THRESHOLD  = 2   # supplement_count <= 2 → limited_supplement_dependency


def run(
    snapshot: StructureSnapshot,
    derived: DerivedMetrics,
) -> Tuple[List[StrengthFlag], List[RiskFlag]]:
    """
    Returns:
      List[StrengthFlag] — structural strengths
      List[RiskFlag]     — structural risks (including omega3 signal)
    """
    strengths = _evaluate_strengths(snapshot, derived.supplement_count)
    risks     = _evaluate_risks(snapshot, derived.supplement_count)
    return strengths, risks


# ---------------------------------------------------------------------------
# Strength flags
# ---------------------------------------------------------------------------

def _evaluate_strengths(
    snapshot: StructureSnapshot,
    supplement_count: int,
) -> List[StrengthFlag]:
    flags: List[StrengthFlag] = []

    if snapshot.has_main_protein:
        flags.append(StrengthFlag(
            type="formula_structure",
            code="clear_main_protein_present",
            priority="high",
        ))

    if snapshot.has_calcium_source:
        flags.append(StrengthFlag(
            type="formula_structure",
            code="clear_calcium_source_present",
            priority="high",
        ))

    if supplement_count <= _SUPPLEMENT_LOW_THRESHOLD:
        flags.append(StrengthFlag(
            type="formula_structure",
            code="limited_supplement_dependency",
            priority="medium",
        ))

    return flags


# ---------------------------------------------------------------------------
# Risk flags
# ---------------------------------------------------------------------------

def _evaluate_risks(
    snapshot: StructureSnapshot,
    supplement_count: int,
) -> List[RiskFlag]:
    flags: List[RiskFlag] = []

    if not snapshot.has_calcium_source:
        flags.append(RiskFlag(
            type="formula_structure",
            severity="high",
            code="missing_calcium_source",
            priority=1,
            recommended_action_code="increase_calcium_support",
        ))

    # omega3_support: structural signal (not AAFCO value)
    if not snapshot.has_omega3_support:
        flags.append(RiskFlag(
            type="formula_structure",
            severity="medium",
            code="missing_omega3_support",
            priority=3,
            recommended_action_code="add_omega3_support",
        ))

    if supplement_count >= _SUPPLEMENT_HIGH_THRESHOLD:
        flags.append(RiskFlag(
            type="formula_structure",
            severity="medium",
            code="high_supplement_dependency",
            priority=4,
            recommended_action_code=None,
        ))

    return flags
