"""
Response builder service - converts internal route data to API response format
Includes complete route geometry and waypoint information
"""
from typing import List, Dict
from app.models.response import Route, RouteResponse, LocationPoint, Waypoint, RouteGeometry


class ResponseBuilderService:
    """Response builder service - converts internal data to API response format"""
    
    def build_response(self, routes_data: List[Dict]) -> RouteResponse:
        """
        Build API response from candidate routes data
        
        Args:
            routes_data: List of candidate routes from generation service
            
        Returns:
            RouteResponse with complete route information
        """
        routes = []
        
        for i, route_data in enumerate(routes_data):
            try:
                # Extract route info
                route_info = route_data.get('route_info', {})
                waypoints_data = route_data.get('waypoints', {})
                metadata = route_data.get('metadata', {})
                
                # Build waypoints list
                waypoints = []
                for place_data in waypoints_data.get('places', []):
                    waypoint = Waypoint(
                        place_id=place_data.get('place_id', ''),
                        name=place_data.get('name', 'Unknown Place'),
                        category=place_data.get('category', 'other'),
                        search_category=place_data.get('search_category', 'other'),
                        location=LocationPoint(
                            lat=place_data.get('location', {}).get('lat', 0.0),
                            lng=place_data.get('location', {}).get('lng', 0.0),
                            name=place_data.get('name', 'Unknown Place')
                        ),
                        rating=place_data.get('rating', 0.0),
                        distance_km=place_data.get('distance_km', 0.0)
                    )
                    waypoints.append(waypoint)
                
                # Build route geometry
                geometry = RouteGeometry(
                    overview_polyline=route_info.get('overview_polyline', {'points': ''}),
                    viewport=route_info.get('viewport', {})
                )
                
                # Parse duration to get a readable format
                duration_str = route_info.get('duration', '0s')
                distance_m = route_info.get('distance', 0)
                
                # Generate route name based on waypoints
                if waypoints:
                    waypoint_names = [wp.name for wp in waypoints[:2]]  # First 2 waypoints
                    if len(waypoints) > 2:
                        route_name = f"Via {waypoint_names[0]}, {waypoint_names[1]} +{len(waypoints)-2} more"
                    else:
                        route_name = f"Via {' & '.join(waypoint_names)}"
                else:
                    route_name = f"Route {i+1}"
                
                # Build route object
                route = Route(
                    id=route_data.get('id', f"route_{i+1}"),
                    name=route_name,
                    distance=distance_m,
                    duration=duration_str,
                    waypoints=waypoints,
                    geometry=geometry,
                    metadata=metadata,
                    score=route_data.get('score', 0.8)  # Default score
                )
                routes.append(route)
                
            except Exception as e:
                print(f"⚠️ Error building route {i+1}: {str(e)}")
                continue
        
        return RouteResponse(
            success=True,
            message=f"Successfully generated {len(routes)} routes",
            routes=routes,
            total_count=len(routes)
        )
