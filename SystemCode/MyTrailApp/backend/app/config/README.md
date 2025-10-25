# Configuration Module Guide

## 📁 Directory Structure

```
app/config/
├── __init__.py          # Package entry point that exposes primary settings
├── config.py           # Core configuration (API keys, limits, etc.)
├── place_types.py      # Unified place type configuration
└── README.md          # This guide
```

## 🔧 Key Configuration Files

### 1. config.py – Primary Settings
- **Google Maps API Key**: API key used by mapping services
- **API Call Limits**: Maximum requests per day
- **Route Generation Parameters**: Maximum number of generated routes, etc.

### 2. place_types.py – Unified Place Type Configuration

#### 📊 Statistics
- **Common Google Types**: 40 curated Google Places API types
- **Custom Categories**: 13 core categories
- **Multilingual Keywords**: Chinese and English keyword mappings

#### 🏷️ Core Categories

| Category     | Google Types                               | Description           |
| ------------ | ------------------------------------------ | --------------------- |
| `park`       | park, national_park                        | Parks and green space |
| `restaurant` | restaurant                                 | Restaurants           |
| `cafe`       | cafe, coffee_shop                          | Cafés                 |
| `shopping`   | shopping_mall, store, market               | Shopping venues       |
| `culture`    | museum, art_gallery, library               | Cultural attractions  |
| `sports`     | gym, fitness_center, sports_complex        | Sports and fitness    |
| `transport`  | bus_station, train_station, subway_station | Transport hubs        |
| `health`     | hospital, pharmacy                         | Healthcare facilities |

#### 🌍 Multilingual Support
```python
"park": ["park", "garden", "公园", "花园", "绿地", "植物园"]
"restaurant": ["restaurant", "dining", "餐厅", "餐馆", "用餐"]
"cafe": ["cafe", "coffee", "咖啡", "咖啡厅", "茶馆"]
```

## 🚀 Usage

### Import Configuration
```python
from app.config import settings
from app.config.place_types import (
    get_google_types_for_category,
    is_valid_google_type,
    CUSTOM_CATEGORY_MAPPING,
    PLACE_TYPE_KEYWORDS
)
```

### Retrieve Google Types
```python
# Get Google types for a custom category
google_types = get_google_types_for_category("park")
# Returns: ["park", "national_park"]

# Validate whether a Google type is supported
is_valid = is_valid_google_type("restaurant")  # True
is_valid = is_valid_google_type("invalid_type")  # False
```

### NLP Keyword Matching
```python
# Example usage in the NLP service
keywords = PLACE_TYPE_KEYWORDS["park"]
# Returns: ["park", "garden", ...] (list also contains Chinese keywords)
```

## 🎯 Design Principles

1. **Consistency**: Centralized management for all place-type configuration
2. **Simplicity**: Keep 40 core Google types to avoid redundancy
3. **Extensibility**: Easy to add new categories and keywords
4. **Multilingual Support**: Chinese and English keywords for NLP processing
5. **Validation**: Built-in type validation to ensure correct API usage

## 📈 Benefits

- ✅ **Alignment**: Shared type definitions across frontend, backend, and NLP services
- ✅ **Easy Maintenance**: Update a single file to adjust categories
- ✅ **Type Safety**: Automatically validate Google Places API types
- ✅ **Internationalization**: Multilingual keyword matching
- ✅ **Performance**: Predefined types reduce API errors
