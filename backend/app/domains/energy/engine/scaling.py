from typing import Optional

def calculate_scaling_factor(target_energy_kcal: float, target_calories_kcal: float) -> float:
    if target_energy_kcal <= 0:
        raise ValueError("target_energy_kcal must be > 0")
    if target_calories_kcal <= 0:
        raise ValueError("target_calories_kcal must be > 0")
    return round(target_energy_kcal / target_calories_kcal, 4)