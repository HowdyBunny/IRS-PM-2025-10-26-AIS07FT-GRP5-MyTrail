"""
User feedback models for route selection data
"""
from typing import List, Dict, Any
from pydantic import BaseModel


class RouteFeedback(BaseModel):
    """Route feedback model"""
    id: str
    selected: int  # 1 for selected, 0 for not selected
    name: str
    distance: int  # Distance in meters
    duration: str  # Duration string (e.g., "3848s")
    waypoints: List[Dict[str, Any]]  # Waypoint information
    score: float = 0.0  # Route score
    criteria: Dict[str, Any] = {}  # User criteria for training
