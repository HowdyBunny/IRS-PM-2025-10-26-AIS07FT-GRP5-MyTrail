from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional


class MapService(ABC):
    """Map service abstract interface"""

    @abstractmethod
    async def find_nearby_places(
        self, center: Tuple[float, float], radius_km: float, categories: List[str]
    ) -> List[Dict]:
        """Search for nearby places of specified types"""
        pass

    @abstractmethod
    async def get_directions(
        self,
        origin: Tuple[float, float],
        waypoints: List[str] = None,
    ) -> Dict:
        """Get route information

        Args:
            origin: Origin coordinates (lat, lng), destination is the same as origin
            waypoints: List of Google Places IDs for waypoints
        """
        pass
