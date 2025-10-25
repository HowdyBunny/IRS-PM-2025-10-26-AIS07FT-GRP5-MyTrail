# Google Maps API Testing Guide

## Test File Structure

Each interface has its own test file:

```
test/
├── README.md                        # Testing guide
├── test_find_nearby_places.py      # Test place search interface
├── test_simple_directions.py       # Test route planning interface
└── test_get_elevation.py           # Test elevation data interface (to be implemented)
```

## Quick Start

### 1. Set API Key

Set API Key in `backend/app/config.py`:

```python
class Settings(BaseSettings):
    # Google Maps API configuration
    google_maps_api_key: str = "your_api_key_here"  # Set your API Key here
```

### 2. Run Tests

**Test place search interface:**
```bash
cd backend
python test/test_find_nearby_places.py
```

**Test route planning interface:**
```bash
cd backend
python test/test_simple_directions.py
```

## Currently Available Tests

### find_nearby_places Interface Test

Test scenarios:
- Search for parks
- Search for restaurants  
- Multi-type search

**Expected output:**
```
🔍 Testing find_nearby_places interface...
📍 Test scenario 1: Search for parks in Singapore city center
✅ Success! Found 5 parks:
  1. Singapore Botanic Gardens
     Rating: 4.6 (1269 reviews)
     Distance: 1.2km
     Address: 1 Cluny Rd, Singapore 259569
```

### get_directions Interface Test

Test scenarios:
- Fixed origin and destination route
- Route with waypoints

**Expected output:**
```
🔍 Testing the simplest get_directions functionality...
📍 Test: Fixed origin and destination route
✅ Basic test successful!
📍 Test: Route with waypoints
✅ Waypoint test successful!
```

## Common Issues

| Error Message             | Cause               | Solution                                  |
| ------------------------- | ------------------- | ----------------------------------------- |
| `Please set in config.py` | API Key not set     | Set google_maps_api_key in config.py      |
| `API key invalid`         | API Key error       | Check if Key is correct                   |
| `Places API not enabled`  | Service not enabled | Enable Places API in Google Cloud Console |
| `Routes API not enabled`  | Service not enabled | Enable Routes API in Google Cloud Console |
| `API quota exceeded`      | Quota exceeded      | Wait for reset or upgrade plan            |
| `Failed to fetch places`  | Network issue       | Check network connection                  |

## Getting API Key

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the following APIs:
   - **Places API** (for place search)
   - **Routes API** (for route planning)
3. Create API key
4. Set environment variables

## Notes

- Google Maps API charges per call
- Pay attention to daily call limits
- Test results may vary by region
- Routes API needs to be enabled separately
