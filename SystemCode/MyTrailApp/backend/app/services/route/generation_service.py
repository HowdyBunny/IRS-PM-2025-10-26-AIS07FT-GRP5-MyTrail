import random
import math
from typing import List, Dict, Tuple, Optional
from app.services.map.map_service import MapService
from app.services.map.google_map_service import GoogleMapService
from app.services.route.two_opt_optimizer import optimize_waypoint_order_by_two_opt
from app.models.request import RouteCriteria


class RouteGenerationService:
    """
    Route generation service - responsible for searching nearby places and generating candidate routes based on user requirements
    """

    def __init__(self, map_service=None):
        if map_service:
            self.map_service = map_service
        else:
            self.map_service = GoogleMapService()

    def _optimize_waypoint_order_by_angle(
        self, center: Tuple[float, float], waypoints: List[Dict]
    ) -> List[Dict]:
        """
        Order waypoints by their bearing from the center to create a clockwise path and avoid backtracking.

        Args:
            center: Center coordinates (lat, lng)
            waypoints: List of waypoint dictionaries

        Returns:
            Waypoints sorted by bearing
        """
        if len(waypoints) <= 1:
            return waypoints

        def calculate_bearing(center_lat, center_lng, point_lat, point_lng):
            """Calculate the bearing (0-360 degrees) from the center to a waypoint."""
            lat1, lng1 = math.radians(center_lat), math.radians(center_lng)
            lat2, lng2 = math.radians(point_lat), math.radians(point_lng)

            d_lng = lng2 - lng1

            y = math.sin(d_lng) * math.cos(lat2)
            x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(
                lat2
            ) * math.cos(d_lng)

            bearing = math.atan2(y, x)
            bearing = math.degrees(bearing)
            bearing = (bearing + 360) % 360  # Normalize to 0-360 degrees

            return bearing

        # Compute the bearing for each waypoint
        waypoints_with_angle = []
        for wp in waypoints:
            lat = wp["location"]["lat"]
            lng = wp["location"]["lng"]
            angle = calculate_bearing(center[0], center[1], lat, lng)
            waypoints_with_angle.append((wp, angle))

        # Sort by bearing (clockwise)
        waypoints_with_angle.sort(key=lambda x: x[1])

        optimized = [wp[0] for wp in waypoints_with_angle]
        return optimize_waypoint_order_by_two_opt(optimized)

    async def generate_candidate_routes(
        self, criteria: RouteCriteria, max_routes: int = 20
    ) -> List[Dict]:
        """
        Generate candidate routes based on user criteria.

        Steps:
        1. Search for places within radius_km/2 of the center
        2. Filter for park, nature, attraction, restaurant types
        3. Randomly select 2-3 waypoints per route
        4. Generate routes with waypoint information

        Args:
            criteria: Route generation criteria
            max_routes: Maximum number of routes to generate

        Returns:
            List of candidate routes with route info and waypoint details
        """
        center_tuple = (criteria.center.lat, criteria.center.lng)
        search_radius = (
            criteria.radius_km / 2
        )  # Use half the radius for waypoint search

        # Step 1: Define target categories for waypoint search
        target_categories = ["park", "nature", "attraction", "restaurant"]

        # Step 2: Search for places in each category
        print(f"🔍 Searching for waypoints within {search_radius}km of center...")
        all_waypoint_candidates = []

        for category in target_categories:
            try:
                places = await self.map_service.find_nearby_places(
                    center=center_tuple, radius_km=search_radius, categories=[category]
                )

                # Add category info to each place for tracking
                for place in places:
                    place["search_category"] = category
                    all_waypoint_candidates.append(place)

                print(f"   Found {len(places)} {category} places")

            except Exception as e:
                print(f"   ⚠️ Error searching {category}: {str(e)}")
                continue

        if not all_waypoint_candidates:
            print("❌ No waypoint candidates found")
            return []

        print(f"✅ Total waypoint candidates: {len(all_waypoint_candidates)}")

        # Step 3: Generate candidate routes
        candidate_routes = []

        for route_idx in range(max_routes):
            # Randomly select 2-3 waypoints for this route
            num_waypoints = random.randint(2, 3)

            if len(all_waypoint_candidates) < num_waypoints:
                # If not enough candidates, use all available
                selected_waypoints = all_waypoint_candidates.copy()
            else:
                # Randomly sample waypoints
                selected_waypoints = random.sample(
                    all_waypoint_candidates, num_waypoints
                )

            # Optimize by bearing to avoid backtracking
            optimized_waypoints = self._optimize_waypoint_order_by_angle(
                center_tuple, selected_waypoints
            )

            # Extract Place IDs for route generation
            waypoint_place_ids = [place["place_id"] for place in optimized_waypoints]

            try:
                # Step 4: Generate the actual route using Google Routes API
                print(
                    f"🗺️ Generating route {route_idx + 1} with {len(optimized_waypoints)} waypoints..."
                )

                route_data = await self.map_service.get_directions(
                    origin=center_tuple, waypoints=waypoint_place_ids
                )

                if not route_data:
                    print(f"   ⚠️ Failed to generate route {route_idx + 1}")
                    continue

                # Step 5: Build comprehensive route candidate
                route_candidate = {
                    "id": f"route_{route_idx + 1}",
                    "route_info": {
                        "overview_polyline": route_data.get("overview_polyline", {}),
                        "duration": route_data.get("duration", "0s"),
                        "distance": route_data.get("distance", 0),
                        "viewport": route_data.get("viewport", {}),
                    },
                    "waypoints": {
                        "count": len(optimized_waypoints),
                        "places": optimized_waypoints,
                        "place_ids": waypoint_place_ids,
                    },
                    "metadata": {
                        "center": center_tuple,
                        "search_radius_km": search_radius,
                        "route_type": criteria.route_type,
                        "categories_used": list(
                            set([p["search_category"] for p in optimized_waypoints])
                        ),
                    },
                    "criteria": criteria.dict(),  # Store original criteria
                }

                candidate_routes.append(route_candidate)

                # Parse duration for logging
                duration_str = route_data.get("duration", "0s")
                distance_m = route_data.get("distance", 0)

                print(f"   ✅ Route {route_idx + 1}: {distance_m}m, {duration_str}")
                print(f"      Waypoints: {[p['name'] for p in optimized_waypoints]}")

            except Exception as e:
                print(f"   ❌ Error generating route {route_idx + 1}: {str(e)}")
                continue

        print(f"🎉 Generated {len(candidate_routes)} candidate routes")
        return candidate_routes
