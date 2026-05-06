from .constants import EnergyConstants


def bw075(weight_kg: float) -> float:
    return weight_kg ** EnergyConstants.RER_EXPONENT


def calculate_rer(weight_kg: float) -> float:
    if weight_kg <= 0:
        raise ValueError("weight_kg must be > 0")
    return EnergyConstants.RER_BASE_COEFFICIENT * bw075(weight_kg)