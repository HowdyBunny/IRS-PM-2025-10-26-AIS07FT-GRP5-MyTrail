from typing import List, Optional
from pydantic import BaseModel

class Center(BaseModel):
    lat: float
    lng: float

class QueryRequest(BaseModel):
    query: str
    center: Center

class RouteCriteria(BaseModel):
    center: Center
    radius_km: float = 5
    duration_min: Optional[int] = 30
    distance_km: Optional[float] = None
    include_categories: List[str] = []
    avoid_categories: List[str] = []
    pet_friendly: bool = False
    elevation_gain_min_m: Optional[int] = None
    route_type: str = "loop"
    time_window: Optional[str] = None
    