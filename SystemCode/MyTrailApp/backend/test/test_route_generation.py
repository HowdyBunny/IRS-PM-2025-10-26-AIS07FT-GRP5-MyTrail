"""
Test script for route generation business logic
Tests the generate_candidate_routes functionality
"""

import asyncio
import sys
import os
import json

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.route.generation_service import RouteGenerationService
from app.models.request import RouteCriteria, Center


async def test_route_generation():
    """Test route generation business logic"""

    print("🚀 Testing Route Generation Business Logic...")
    print("=" * 60)

    try:
        # Create service instance
        service = RouteGenerationService()

        # Test Case 1: Marina Bay Sands area
        print("📍 Test Case 1: Marina Bay Sands Area")
        print("-" * 40)

        criteria = RouteCriteria(
            center=Center(lat=1.2834, lng=103.8607),  # Marina Bay Sands
            radius_km=4.0,  # 4km radius, so search within 2km for waypoints
            duration_min=60,
            route_type="loop",
            include_categories=["park", "nature", "attraction", "restaurant"],
        )

        print(f"Center: ({criteria.center.lat}, {criteria.center.lng})")
        print(
            f"Radius: {criteria.radius_km}km (search within {criteria.radius_km/2}km)"
        )
        print(f"Target categories: park, nature, attraction, restaurant")
        print()

        # Generate candidate routes
        candidate_routes = await service.generate_candidate_routes(
            criteria, max_routes=3
        )

        if candidate_routes:
            print(
                f"🎉 Successfully generated {len(candidate_routes)} candidate routes!"
            )
            print()

            # Display detailed information for each route
            for i, route in enumerate(candidate_routes, 1):
                print(f"📋 Route {i} Details:")
                print(f"   ID: {route['id']}")

                # Route info
                route_info = route["route_info"]
                distance_km = route_info["distance"] / 1000
                print(f"   Distance: {route_info['distance']}m ({distance_km:.2f}km)")
                print(f"   Duration: {route_info['duration']}")
                print(
                    f"   Polyline length: {len(route_info['overview_polyline'].get('points', ''))}"
                )

                # Waypoints info
                waypoints = route["waypoints"]
                print(f"   Waypoints: {waypoints['count']} places")

                for j, place in enumerate(waypoints["places"], 1):
                    print(f"     {j}. {place['name']}")
                    print(
                        f"        Category: {place['category']} (searched as: {place['search_category']})"
                    )
                    print(f"        Rating: {place['rating']}")
                    print(f"        Distance from center: {place['distance_km']}km")

                # Metadata
                metadata = route["metadata"]
                print(f"   Categories used: {metadata['categories_used']}")
                print(f"   Route type: {metadata['route_type']}")
                print()
        else:
            print("❌ No candidate routes generated")
            return False

        # Test Case 2: Different location - Singapore city center
        print("=" * 60)
        print("📍 Test Case 2: Singapore City Center")
        print("-" * 40)

        criteria2 = RouteCriteria(
            center=Center(lat=1.2966, lng=103.7764),  # Singapore city center
            radius_km=3.0,
            duration_min=45,
            route_type="loop",
        )

        print(f"Center: ({criteria2.center.lat}, {criteria2.center.lng})")
        print(
            f"Radius: {criteria2.radius_km}km (search within {criteria2.radius_km/2}km)"
        )
        print()

        candidate_routes2 = await service.generate_candidate_routes(
            criteria2, max_routes=2
        )

        if candidate_routes2:
            print(f"🎉 Generated {len(candidate_routes2)} more routes!")

            # Quick summary
            for route in candidate_routes2:
                route_info = route["route_info"]
                waypoints = route["waypoints"]
                distance_km = route_info["distance"] / 1000

                print(
                    f"   {route['id']}: {distance_km:.2f}km, {route_info['duration']}, {waypoints['count']} waypoints"
                )
                waypoint_names = [p["name"] for p in waypoints["places"]]
                print(f"      Via: {', '.join(waypoint_names)}")

        print()
        print("✅ Route Generation Test Completed Successfully!")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


async def test_edge_cases():
    """Test edge cases for route generation"""

    print("\n🧪 Testing Edge Cases...")
    print("=" * 40)

    service = RouteGenerationService()

    # Edge Case 1: Very small radius
    print("🔍 Edge Case 1: Very small search radius")
    criteria_small = RouteCriteria(
        center=Center(lat=1.2834, lng=103.8607),
        radius_km=0.5,  # Very small radius
        route_type="loop",
    )

    routes_small = await service.generate_candidate_routes(criteria_small, max_routes=2)
    print(f"   Small radius result: {len(routes_small)} routes generated")

    # Edge Case 2: Remote location (might have fewer places)
    print("🏝️ Edge Case 2: Remote location")
    criteria_remote = RouteCriteria(
        center=Center(
            lat=1.3521, lng=103.8198
        ),  # Somewhere in Singapore but less central
        radius_km=2.0,
        route_type="loop",
    )

    routes_remote = await service.generate_candidate_routes(
        criteria_remote, max_routes=2
    )
    print(f"   Remote location result: {len(routes_remote)} routes generated")

    print("✅ Edge case testing completed")


if __name__ == "__main__":
    print("🔧 Starting Route Generation Tests...")

    # Run main test
    success = asyncio.run(test_route_generation())

    if success:
        # Run edge case tests
        asyncio.run(test_edge_cases())
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)
