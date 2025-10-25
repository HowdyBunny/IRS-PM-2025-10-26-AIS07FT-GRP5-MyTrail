from pydantic import BaseModel, validator
from typing import List, Dict, Any, Tuple, Optional
class RouteCriteria(BaseModel):
    radius_km: float = 5.0
    duration_min: int = 30
    distance_km: Optional[float] = None
    include_categories: List[str] = ["park"]
    avoid_categories: List[str] = []
    pet_friendly: bool = False
    elevation_gain_min_m: Optional[int] = None
    route_type: str = "loop"  # "loop" | "out-and-back"
    time_window: Optional[Dict[str, str]] = None  # {"start_local":"HH:MM","end_local":"HH:MM"}

    @validator("route_type")
    def _rt(cls, v):
        return v if v in ("loop","out-and-back") else "loop"