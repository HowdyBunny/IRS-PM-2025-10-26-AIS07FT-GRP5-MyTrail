import httpx
import asyncio
from typing import List, Dict, Tuple, Optional
from app.services.map.map_service import MapService
from app.services.map.api_counter import api_counter
from app.config import settings
from app.config.place_types import (
    get_google_types_for_category,
    is_valid_google_type,
    get_categories_for_google_type,
    get_primary_category_for_types,
    filter_supported_types,
    COMMON_GOOGLE_TYPES,
)


class GoogleMapService(MapService):
    """Google Maps API service implementation"""

    def __init__(self):
        self.api_key = settings.google_maps_api_key
        self.nearby_search_url = "https://places.googleapis.com/v1/places:searchNearby"
        self.routes_url = "https://routes.googleapis.com/directions/v2:computeRoutes"

        if not self.api_key:
            raise ValueError("Google Maps API Key is required")

    async def find_nearby_places(
        self, center: Tuple[float, float], radius_km: float, categories: List[str]
    ) -> List[Dict]:
        """Search nearby places using Google Places API (New) v1"""
        # Check API call limit
        if not api_counter.can_make_call():
            raise Exception(
                f"API call limit exceeded. Max calls per day: {settings.max_api_calls_per_day}"
            )

        center_lat, center_lng = center
        radius_m = radius_km * 1000  # Convert to meters

        # Map our categories to Google Places types
        google_types = self._map_categories_to_google_types(categories)

        # Build request body for new API
        body = {
            "maxResultCount": 20,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": center_lat, "longitude": center_lng},
                    "radius": radius_m,
                }
            },
        }

        # Add type filtering if categories are specified
        if google_types:
            body["includedTypes"] = google_types

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.nearby_search_url,
                    headers={
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": self.api_key,
                        "X-Goog-FieldMask": "places.displayName,places.location,places.rating,places.id,places.types",
                    },
                    json=body,
                    timeout=10.0,
                )
                response.raise_for_status()

                # Record API call
                api_counter.record_call()

                data = response.json()

                # Convert to our standard format
                places = data.get("places", [])
                return self._convert_places_to_standard_format(places, center)

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = f" - {error_data.get('error', {}).get('message', '')}"
            except:
                pass

            if e.response.status_code == 429:
                raise Exception("API quota exceeded")
            elif e.response.status_code == 403:
                raise Exception("API key invalid or Places API not enabled")
            elif e.response.status_code == 400:
                raise Exception(
                    f"Bad request (400): Invalid request parameters{error_detail}"
                )
            else:
                raise Exception(
                    f"Places API error: {e.response.status_code}{error_detail}"
                )
        except Exception as e:
            raise Exception(f"Failed to fetch places: {str(e)}")

    async def _find_nearest_navigable_point(
        self, center: Tuple[float, float]
    ) -> Tuple[str, Tuple[float, float]]:
        """Find the nearest navigable point using Places API

        Returns:
            Tuple of (place_id, (lat, lng)) or (None, original_coordinates)
        """
        # Check API call limit
        if not api_counter.can_make_call():
            raise Exception(
                f"API call limit exceeded. Max calls per day: {settings.max_api_calls_per_day}"
            )

        center_lat, center_lng = center
        radius_m = 100  # Search within 100 meters

        # Build request body to find any nearby place
        body = {
            "maxResultCount": 1,  # Only need the closest one
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": center_lat, "longitude": center_lng},
                    "radius": radius_m,
                }
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.nearby_search_url,
                    headers={
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": self.api_key,
                        "X-Goog-FieldMask": "places.location,places.id",
                    },
                    json=body,
                    timeout=10.0,
                )
                response.raise_for_status()

                # Record API call
                api_counter.record_call()

                data = response.json()
                places = data.get("places", [])

                if places:
                    # Use the Place ID and location of the nearest place
                    place = places[0]
                    place_id = place.get("id", "")
                    location = place.get("location", {})
                    lat = location.get("latitude", center_lat)
                    lng = location.get("longitude", center_lng)
                    return (place_id, (lat, lng))
                else:
                    # If no places found, return None and original coordinates
                    return (None, center)

        except Exception as e:
            # If search fails, return None and original coordinates
            print(f"⚠️ Warning: Could not find nearest navigable point: {str(e)}")
            return (None, center)

    async def get_directions(
        self, origin: Tuple[float, float], waypoints: List[str] = None
    ) -> Dict:
        """Get route information using Google Routes API - origin and destination are the same

        Args:
            origin: Origin coordinates (lat, lng), destination is the same as origin
            waypoints: List of Google Places IDs for waypoints
        """
        # Check API call limit
        if not api_counter.can_make_call():
            raise Exception(
                f"API call limit exceeded. Max calls per day: {settings.max_api_calls_per_day}"
            )

        # Find the nearest navigable point to use as precise origin/destination
        print(f"🔍 Finding nearest navigable point to {origin}...")
        place_id, navigable_coords = await self._find_nearest_navigable_point(origin)

        if place_id:
            print(f"📍 Found nearest place: {place_id} at {navigable_coords}")
            # Build request body using Place ID for origin/destination
            request_body = self._build_routes_request_body(place_id, waypoints)
        else:
            print(f"❌ No nearby place found near {origin}")
            raise Exception(
                f"Could not find a navigable place near coordinates {origin}. Please try a different location or ensure you're near a recognizable place."
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.routes_url,
                    headers={
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": self.api_key,
                        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.viewport",
                    },
                    json=request_body,
                    timeout=10.0,
                )
                response.raise_for_status()

                # Record API call
                api_counter.record_call()

                data = response.json()

                # Convert to standard format
                return self._convert_routes_response(data)

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = f" - {error_data.get('error', {}).get('message', '')}"
            except:
                pass

            if e.response.status_code == 429:
                raise Exception("API quota exceeded")
            elif e.response.status_code == 403:
                raise Exception("API key invalid or Routes API not enabled")
            elif e.response.status_code == 400:
                raise Exception(
                    f"Bad request (400): Invalid request parameters{error_detail}"
                )
            else:
                raise Exception(
                    f"Routes API error: {e.response.status_code}{error_detail}"
                )
        except Exception as e:
            raise Exception(f"Failed to get directions: {str(e)}")

    def _build_routes_request_body(
        self, origin_place_id: str, waypoints: List[str] = None
    ) -> Dict:
        """Build request body for Google Routes API using Place ID for origin/destination"""
        request_body = {
            "origin": {"placeId": origin_place_id},
            "destination": {"placeId": origin_place_id},  # Same place for loop route
            "travelMode": "WALK",  # Fixed to walking mode
        }

        # Add waypoints using Place IDs if any
        if waypoints:
            request_body["intermediates"] = []
            for place_id in waypoints:
                request_body["intermediates"].append({"placeId": place_id})

        return request_body

    def _convert_routes_response(self, data: Dict) -> Dict:
        """Convert Routes API response to standard format"""
        if not data.get("routes"):
            return {}

        route = data["routes"][0]

        # Extract basic information
        duration = route.get("duration", "0s")
        distance = route.get("distanceMeters", 0)
        polyline = route.get("polyline", {}).get("encodedPolyline", "")

        # Extract geometry information for frontend display
        viewport = route.get("viewport", {})

        # Build response with complete route and geometry information
        return {
            "overview_polyline": {"points": polyline},
            "duration": duration,
            "distance": distance,
            "viewport": viewport,
        }

    def _map_categories_to_google_types(self, categories: List[str]) -> List[str]:
        """Map our categories to Google Places types using official Table A types"""
        google_types = []
        for category in categories:
            # Get Google types for this category from our unified config
            category_google_types = get_google_types_for_category(category)
            google_types.extend(category_google_types)

        # Remove duplicates and validate all types
        unique_types = []
        for google_type in set(google_types):
            if is_valid_google_type(google_type):
                unique_types.append(google_type)

        return unique_types

    def _convert_places_to_standard_format(
        self, places: List[Dict], center: Tuple[float, float]
    ) -> List[Dict]:
        """Convert Google Places API (New) v1 response to standard format"""
        center_lat, center_lng = center
        converted_places = []

        for place in places:
            # Extract basic information from new API format
            name = place.get("displayName", {}).get("text", "Unknown Place")

            # Extract location information from new API format
            location = place.get("location", {})
            lat = location.get("latitude", 0.0)
            lng = location.get("longitude", 0.0)

            # Calculate distance
            distance_km = self._calculate_distance(center_lat, center_lng, lat, lng)

            # Extract and standardize place types from new API format
            raw_place_types = place.get("types", [])
            primary_type = place.get("primaryType", "")

            # Combine and deduplicate types (primary type first)
            all_types = []
            if primary_type:
                all_types.append(primary_type)
            all_types.extend([t for t in raw_place_types if t != primary_type])

            # Filter and standardize place types using our configuration
            standardized_types = self._standardize_place_types(all_types)
            category = self._determine_category(standardized_types)

            # Extract business status from new API format
            business_status = place.get("businessStatus", "UNKNOWN")

            # Extract price level from new API format
            price_level = place.get("priceLevel", None)

            # Extract rating information from new API format
            rating = place.get("rating", 0.0)
            user_ratings_total = place.get("userRatingCount", 0)

            # Extract photo information from new API format
            photos = place.get("photos", [])
            photo_references = [
                photo.get("name", "").split("/")[-1]  # Extract photo ID from name
                for photo in photos
                if photo.get("name")
            ]

            # Extract formatted address from new API format
            formatted_address = place.get("formattedAddress", "")

            # Extract plus code from new API format
            plus_code = place.get("plusCode", {})
            plus_code_dict = {}
            if plus_code:
                plus_code_dict = {
                    "compound_code": plus_code.get("compoundCode", ""),
                    "global_code": plus_code.get("globalCode", ""),
                }

            # Build standard format
            place_data = {
                "place_id": place.get("id", f"google_{hash(name)}"),
                "name": name,
                "location": {"lat": lat, "lng": lng},
                "category": category,
                "rating": rating,
                "user_ratings_total": user_ratings_total,
                "distance_km": round(distance_km, 2),
                "formatted_address": formatted_address,
                "place_types": standardized_types,
                "google_types": all_types,  # Keep original Google types for reference
                "business_status": business_status,
                "is_open_now": None,  # Not available in new API
                "price_level": price_level,
                "photo_references": photo_references,
                "plus_code": plus_code_dict,
                "icon": place.get("icon", ""),
                "icon_background_color": place.get("iconBackgroundColor", ""),
                "scope": "GOOGLE",  # New API always returns Google places
                "reference": place.get("id", ""),
            }

            converted_places.append(place_data)

        return converted_places

    def _standardize_place_types(self, google_types: List[str]) -> List[str]:
        """
        Standardize Google place types to our supported types.
        Uses the unified place_types configuration for filtering and deduplication.
        """
        return filter_supported_types(google_types)

    def _determine_category(self, place_types: List[str]) -> str:
        """
        Determine our standard category based on Google place types.
        Uses the unified place_types configuration for consistent mapping.
        """
        return get_primary_category_for_types(place_types)

    def _calculate_distance(
        self, lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """Calculate distance between two points (Haversine formula)"""
        import math

        R = 6371  # Earth radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
