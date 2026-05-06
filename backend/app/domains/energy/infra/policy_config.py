from typing import Optional
from app.domains.energy.engine.constants import EnergyConstants


class EnergyPolicyConfig:
    """
    Current implementation uses static defaults.

    Future extension points:
    - DB-backed configurable coefficients
    - environment-specific policy
    - admin-managed activity/profile presets
    """
    constants = EnergyConstants