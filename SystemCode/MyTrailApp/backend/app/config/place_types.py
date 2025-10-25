"""
Place Types Configuration for Trail/Route Generation
Simplified configuration with only essential types and functions.
"""

from typing import Dict, List


# Essential Google Places API types for trail/route generation
COMMON_GOOGLE_TYPES = {
    # Nature & Recreation
    "park",
    "national_park",
    "tourist_attraction",
    "natural_feature",
    "hiking_area",
    "zoo",
    "aquarium",
    "marina",
    # Food & Dining
    "restaurant",
    "cafe",
    "coffee_shop",
    "bakery",
    "fast_food_restaurant",
    "bar",
    # Shopping
    "shopping_mall",
    "store",
    "market",
    "convenience_store",
    "supermarket",
    # Culture & Entertainment
    "museum",
    "art_gallery",
    "library",
    "movie_theater",
    # Sports & Fitness
    "gym",
    "fitness_center",
    "sports_complex",
    "swimming_pool",
    "golf_course",
    # Transportation
    "bus_station",
    "train_station",
    "subway_station",
    "airport",
    "parking",
    # Services
    "hospital",
    "pharmacy",
    "bank",
    "gas_station",
    "rest_stop",
    # Accommodation
    "hotel",
    "lodging",
}

# Category mapping: custom categories -> Google types
CUSTOM_CATEGORY_MAPPING = {
    "park": ["park", "national_park"],
    "nature": ["hiking_area", "park"],
    "waterfront": ["marina", "tourist_attraction"],
    "restaurant": ["restaurant"],
    "cafe": ["cafe", "coffee_shop"],
    "food": ["restaurant", "cafe", "bakery", "fast_food_restaurant", "bar"],
    "shopping": ["shopping_mall", "store", "market", "supermarket"],
    "culture": ["museum", "art_gallery", "library"],
    "attraction": ["tourist_attraction", "zoo", "aquarium"],
    "sports": ["gym", "fitness_center", "sports_complex"],
    "transport": ["bus_station", "train_station", "subway_station", "airport"],
    "health": ["hospital", "pharmacy"],
    "accommodation": ["hotel", "lodging"],
}

# Reverse mapping: Google type -> categories
GOOGLE_TYPE_TO_CATEGORIES: Dict[str, List[str]] = {}
for category, google_types in CUSTOM_CATEGORY_MAPPING.items():
    for google_type in google_types:
        if google_type not in GOOGLE_TYPE_TO_CATEGORIES:
            GOOGLE_TYPE_TO_CATEGORIES[google_type] = []
        GOOGLE_TYPE_TO_CATEGORIES[google_type].append(category)


def get_google_types_for_category(category: str) -> List[str]:
    """Get Google Places API types for a given custom category."""
    return CUSTOM_CATEGORY_MAPPING.get(category, [])


def get_categories_for_google_type(google_type: str) -> List[str]:
    """Get custom categories for a given Google Places API type."""
    return GOOGLE_TYPE_TO_CATEGORIES.get(google_type, [])


def is_valid_google_type(place_type: str) -> bool:
    """Check if a place type is valid according to our common Google types."""
    return place_type in COMMON_GOOGLE_TYPES


def get_primary_category_for_types(place_types: List[str]) -> str:
    """Get the primary (most relevant) category for a list of place types."""
    # Category priority (higher index = higher priority)
    category_priority = [
        "accommodation",
        "transport",
        "health",
        "sports",
        "shopping",
        "culture",
        "attraction",
        "cafe",
        "restaurant",
        "park",
    ]

    # Find categories for all place types
    found_categories = set()
    for place_type in place_types:
        if is_valid_google_type(place_type):
            categories = get_categories_for_google_type(place_type)
            found_categories.update(categories)

    # Return the highest priority category found
    for category in reversed(category_priority):
        if category in found_categories:
            return category

    # If no priority category found, return first available category
    if found_categories:
        return list(found_categories)[0]

    return "other"


def filter_supported_types(google_types: List[str]) -> List[str]:
    """Filter a list of Google types to only include supported ones."""
    seen = set()
    result = []

    for google_type in google_types:
        if is_valid_google_type(google_type) and google_type not in seen:
            seen.add(google_type)
            result.append(google_type)

    return result


# Keywords for NLP processing (multilingual support)
PLACE_TYPE_KEYWORDS = {
    "park": ["park", "garden", "公园", "花园", "绿地"],
    "nature": ["nature", "natural", "自然", "天然"],
    "waterfront": ["waterfront", "beach", "river", "lake", "海边", "水边", "河岸"],
    "restaurant": ["restaurant", "dining", "餐厅", "餐馆"],
    "cafe": ["cafe", "coffee", "咖啡", "咖啡厅"],
    "food": ["food", "eat", "美食", "吃"],
    "shopping": ["shopping", "mall", "store", "购物", "商场"],
    "culture": ["culture", "museum", "art", "文化", "博物馆"],
    "attraction": ["attraction", "scenic", "景点", "景区"],
    "sports": ["sports", "gym", "fitness", "运动", "健身"],
    "health": ["health", "hospital", "医疗", "医院"],
    "transport": ["transport", "station", "交通", "车站"],
    "accommodation": ["hotel", "lodging", "住宿", "酒店"],
}
