from typing import Dict, Optional

from pydantic import BaseModel


class AdultEnergyProfilesResult(BaseModel):
    profiles: Dict[str, float]
    default_profile: Optional[str] = None