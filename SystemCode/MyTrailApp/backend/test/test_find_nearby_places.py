#!/usr/bin/env python3
"""
Test Google Places API - find_nearby_places interface
"""
import asyncio
import sys
import os

# Add project path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.services.map.google_map_service import GoogleMapService
from app.config import settings


async def test_find_nearby_places():
    """Test find_nearby_places interface"""
    # Check API Key
    api_key = settings.google_maps_api_key
    if not api_key:
        print("❌ Error: Please set google_maps_api_key in config.py")
        print("\nSetup method:")
        print("Add in backend/app/config.py:")
        print("google_maps_api_key: str = 'your_api_key_here'")
        return False

    print("🔍 Testing find_nearby_places interface...")
    print(f"🔑 API Key: {api_key[:10]}...")
    print("-" * 50)

    try:
        # Create service instance
        service = GoogleMapService()

        # Test scenario 1: Search for parks
        print("📍 Test scenario 1: Search for parks in Singapore city center")
        print("   Location: (1.2966, 103.7764)")
        print("   Radius: 2km")
        print("   Type: park")
        print()

        places = await service.find_nearby_places(
            center=(1.2966, 103.7764), radius_km=2.0, categories=["park"]
        )

        if places:
            print(f"✅ Success! Found {len(places)} parks:")
            for i, place in enumerate(places[:3], 1):
                print(f"  {i}. {place['name']}")
                print(f"     ID: {place['place_id']}")
                print(f"     Rating: {place['rating']}")
                print(f"     Distance: {place['distance_km']}km")
                print(f"     Category: {place['category']}")
                print()

            if len(places) > 3:
                print(f"  ... and {len(places) - 3} more places")
        else:
            print("⚠️ No parks found, trying to expand search range...")

            # Retry with expanded search range
            places = await service.find_nearby_places(
                center=(1.2966, 103.7764), radius_km=5.0, categories=["park"]
            )

            if places:
                print(f"✅ Found {len(places)} parks after expanding range")
            else:
                print("❌ Still no parks found after expanding range")
                return False

        # Test scenario 2: Search for restaurants
        print("\n" + "=" * 50)
        print("📍 Test scenario 2: Search for restaurants")
        print("   Location: (1.2966, 103.7764)")
        print("   Radius: 1km")
        print("   Type: restaurant")
        print()

        restaurants = await service.find_nearby_places(
            center=(1.2966, 103.7764), radius_km=1.0, categories=["restaurant"]
        )

        if restaurants:
            print(f"✅ Success! Found {len(restaurants)} restaurants:")
            for i, place in enumerate(restaurants[:2], 1):
                print(f"  {i}. {place['name']} (Rating: {place['rating']})")
        else:
            print("⚠️ No restaurants found")

        # Test scenario 3: Multi-type search
        print("\n" + "=" * 50)
        print("📍 Test scenario 3: Multi-type search")
        print("   Location: (1.2966, 103.7764)")
        print("   Radius: 3km")
        print("   Types: park, restaurant, cafe")
        print()

        multi_places = await service.find_nearby_places(
            center=(1.2966, 103.7764),
            radius_km=3.0,
            categories=["park", "restaurant", "cafe"],
        )

        if multi_places:
            print(f"✅ Success! Found {len(multi_places)} places:")
            # Group by category for display
            by_category = {}
            for place in multi_places:
                category = place["category"]
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(place)

            for category, places_list in by_category.items():
                print(f"  {category}: {len(places_list)} places")
                for place in places_list[:2]:
                    print(f"    - {place['name']}")
        else:
            print("⚠️ Multi-type search found no results")

        print("\n" + "=" * 50)
        print("🎉 find_nearby_places interface test completed!")
        print("✅ All test scenarios executed successfully")
        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")

        # Provide error diagnosis
        error_msg = str(e).lower()
        if "api key" in error_msg or "invalid" in error_msg:
            print("\n💡 Diagnosis: API Key issue")
            print("  1. Check if API Key is correct")
            print("  2. Confirm Places API (New) v1 is enabled")
            print("  3. Check API Key permission settings")
        elif "quota" in error_msg or "limit" in error_msg:
            print("\n💡 Diagnosis: API quota issue")
            print("  1. Check API quota usage")
            print("  2. Wait for quota reset or upgrade plan")
        elif "network" in error_msg or "connection" in error_msg:
            print("\n💡 Diagnosis: Network issue")
            print("  1. Check network connection")
            print("  2. Check firewall settings")
        elif "400" in error_msg:
            print("\n💡 Diagnosis: Bad Request (400)")
            print("  1. Check if Places API (New) v1 is enabled")
            print("  2. Verify API Key has correct permissions")
            print("  3. Check request format and parameters")
            print("  4. Ensure FieldMask includes only valid fields")
        else:
            print(f"\n💡 Diagnosis: Unknown error - {type(e).__name__}")

        return False


async def main():
    """Main function"""
    success = await test_find_nearby_places()

    if success:
        print("\n✅ find_nearby_places interface test passed!")
        sys.exit(0)
    else:
        print("\n❌ find_nearby_places interface test failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
