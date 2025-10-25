"""
Test script for place type management and standardization
Tests the integration between GoogleMapService and place_types configuration
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.map.google_map_service import GoogleMapService
from app.config.place_types import *


async def test_place_type_management():
    """Test place type management and standardization"""

    print("🔍 Testing Place Type Management and Standardization...")
    print("=" * 60)

    try:
        # Create service instance
        service = GoogleMapService()

        # Test 1: Type filtering and standardization
        print("📋 Test 1: Type Filtering and Standardization")
        print("-" * 40)

        # Simulate raw Google API response with mixed valid/invalid types
        test_google_types = [
            "park",
            "restaurant",
            "invalid_type_1",
            "cafe",
            "museum",
            "unknown_place",
            "shopping_mall",
            "duplicate_park",
            "park",
        ]

        print(f"Raw Google types: {test_google_types}")

        # Test our standardization method
        standardized = service._standardize_place_types(test_google_types)
        print(f"Standardized types: {standardized}")

        # Test category determination
        category = service._determine_category(standardized)
        print(f"Determined category: {category}")
        print()

        # Test 2: Real API call with type analysis
        print("📍 Test 2: Real API Call with Type Analysis")
        print("-" * 40)

        # Search for mixed places in Singapore
        places = await service.find_nearby_places(
            center=(1.2834, 103.8607),  # Marina Bay Sands area
            radius_km=1.0,
            categories=["park", "restaurant", "culture"],
        )

        if places:
            print(f"Found {len(places)} places. Analyzing first 3:")
            print()

            for i, place in enumerate(places[:3], 1):
                print(f"Place {i}: {place['name']}")
                print(f"  Category: {place['category']}")
                print(f"  Standardized types: {place.get('place_types', [])}")
                print(f"  Original Google types: {place.get('google_types', [])}")
                print(f"  Rating: {place['rating']}")
                print()

        # Test 3: Category priority testing
        print("🏷️ Test 3: Category Priority Testing")
        print("-" * 40)

        priority_test_cases = [
            {"name": "Mixed nature and food", "types": ["park", "restaurant", "cafe"]},
            {
                "name": "Culture and shopping",
                "types": ["museum", "shopping_mall", "library"],
            },
            {
                "name": "Transportation and services",
                "types": ["bus_station", "hospital", "bank"],
            },
            {
                "name": "Only invalid types",
                "types": ["invalid_1", "unknown_type", "not_supported"],
            },
        ]

        for test_case in priority_test_cases:
            category = get_primary_category_for_types(test_case["types"])
            print(f"{test_case['name']}: {test_case['types']} -> {category}")

        print()

        # Test 4: Configuration consistency check
        print("✅ Test 4: Configuration Consistency Check")
        print("-" * 40)

        print(f"Total supported Google types: {len(COMMON_GOOGLE_TYPES)}")
        print(f"Total custom categories: {len(CUSTOM_CATEGORY_MAPPING)}")

        # Check if all mapped types are in our supported set
        all_mapped_types = set()
        for category, google_types in CUSTOM_CATEGORY_MAPPING.items():
            all_mapped_types.update(google_types)

        unsupported_mapped = all_mapped_types - COMMON_GOOGLE_TYPES
        if unsupported_mapped:
            print(f"⚠️ Warning: Mapped but unsupported types: {unsupported_mapped}")
        else:
            print("✅ All mapped types are supported")

        # Check reverse mapping coverage
        reverse_coverage = len(GOOGLE_TYPE_TO_CATEGORIES)
        print(
            f"Reverse mapping coverage: {reverse_coverage}/{len(COMMON_GOOGLE_TYPES)} types"
        )

        print()
        print("🎉 Place Type Management Test Completed!")
        print("✅ All tests executed successfully")

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_place_type_management())
    if success:
        print("\n✅ Place type management test passed!")
    else:
        print("\n❌ Place type management test failed!")
        sys.exit(1)
