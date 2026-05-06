from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.domains.energy.contracts.requests import EnergyCalculationRequest
from app.domains.energy.contracts.models import EnergyCalculationResult
from app.domains.energy.orchestration.energy_service import EnergyService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["能量计算"])


@router.post(
    "/calculate-energy",
    response_model=EnergyCalculationResult,
)
async def calculate_energy(request: EnergyCalculationRequest) -> EnergyCalculationResult:
    """
    计算宠物每日能量需求。
    现在直接走 app.domains.energy 的标准 service，
    不再在 main.py 中维护一套临时 EnergyRequest / EnergyResponse。
    """
    try:
        result = await asyncio.to_thread(EnergyService.calculate, request)
        return result

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.error(f"能量计算异常：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"能量计算失败：{str(e)}")

    