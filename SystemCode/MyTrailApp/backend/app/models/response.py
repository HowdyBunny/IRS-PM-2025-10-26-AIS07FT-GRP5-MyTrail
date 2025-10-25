"""
Response models for route generation API
Includes route geometry and waypoint information
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class LocationPoint(BaseModel):
    """Location point model"""
    lat: float
    lng: float
    name: Optional[str] = None


class Waypoint(BaseModel):
    """Waypoint model with detailed information"""
    place_id: str
    name: str
    category: str
    search_category: str
    location: LocationPoint
    rating: float
    distance_km: float


class RouteGeometry(BaseModel):
    """Route geometry information"""
    overview_polyline: Dict[str, str]  # {"points": "encoded_polyline"}
    viewport: Dict[str, Any]  # Viewport bounds for map display
    

class Route(BaseModel):
    """Route model with complete information"""
    id: str
    name: str
    distance: int  # Distance in meters
    duration: str  # Duration string (e.g., "3848s")
    waypoints: List[Waypoint]
    geometry: RouteGeometry
    metadata: Dict[str, Any]  # Additional metadata
    score: float = 0.0  # Route score


class RouteResponse(BaseModel):
    """Route response model"""
    success: bool = True
    message: str = "success"
    routes: List[Route] = []
    total_count: int = 0
    criteria: Dict[str, Any] = {}  # User criteria for feedback training
