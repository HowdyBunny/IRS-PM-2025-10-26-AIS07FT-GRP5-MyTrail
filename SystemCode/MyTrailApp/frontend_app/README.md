# MyTrail - Trail Finder App

A production-ready Flutter app for iOS and Android that helps users find personalized hiking trails using natural language input and real-time map visualization.

## Features

- 🗺️ **Interactive Map**: Full-height map centered on user location with real-time route visualization
- 🌈 **Smart Input**: Natural language trail search with animated rainbow gradient border
- 📱 **Route Cards**: Horizontally scrollable cards showing distance, duration, and elevation gain
- 📊 **Trail History**: View past searches and selected routes
- 🎯 **Real-time Updates**: Tap route cards to update map instantly
- 📍 **Location Services**: GPS-based trail suggestions with proper permission handling

## Tech Stack

- **Flutter 3.x** with Dart null-safety
- **State Management**: Riverpod (hooks_riverpod)
- **Maps**: Google Maps Flutter
- **Location**: geolocator with permission handling
- **HTTP**: Dio for API communication
- **JSON Models**: Freezed + json_serializable
- **Environment**: flutter_dotenv
- **UI**: flutter_svg for icons

## Architecture

```
lib/
├── app.dart                    # Main app widget
├── main.dart                   # Entry point
├── core/
│   ├── theme/                  # App theming
│   ├── env/                    # Environment configuration
│   └── utils/                  # Utilities (geo, error handling)
├── data/
│   ├── models/                 # Freezed data models
│   └── api_client.dart         # Dio HTTP client
└── features/
    ├── map/                    # Map, routes, location
    ├── input/                  # Rainbow input widget
    └── history/                # History screen
```

## Getting Started

### Prerequisites

- Flutter SDK (3.9.0 or higher)
- Dart SDK
- Android Studio / Xcode for device testing
- A device or emulator with location services

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mytrail
   ```

2. **Install dependencies**
   ```bash
   flutter pub get
   ```

3. **Generate code**
   ```bash
   flutter pub run build_runner build
   ```

4. **Create environment file & Configure Google Maps**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your API configuration.
   
   **Google Maps Setup:**
   - Get a Google Maps API key from [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Maps SDK for Android and iOS
   - Replace `YOUR_GOOGLE_MAPS_API_KEY_HERE` in:
     - `ios/Runner/Info.plist`
     - `android/app/src/main/AndroidManifest.xml`

5. **Run the app**
   ```bash
   flutter run
   ```

### Required Permissions

#### iOS (ios/Runner/Info.plist)
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>This app needs location access to find trails near you.</string>
```

#### Android (android/app/src/main/AndroidManifest.xml)
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.INTERNET" />
```

## API Integration

The app integrates with a RESTful API for trail suggestions and history.

### Endpoints

#### POST /api/v1/routes/suggest
Request trail suggestions based on natural language constraints.

**Request Example:**
```json
{
  "center": {"lat": 1.2966, "lng": 103.7764},
  "radius_km": 5,
  "duration_min": 30,
  "include_categories": ["park", "waterfront"],
  "avoid_categories": ["retail_core"],
  "pet_friendly": true,
  "elevation_gain_min_m": 40,
  "route_type": "loop",
  "time_window": "evening"
}
```

**Response Example:**
```json
{
  "api_version": "1.0",
  "generated_at": "2025-09-03T15:41:00Z",
  "units": "metric",
  "constraints_echo": {
    "center": { "lat": 1.2966, "lng": 103.7764 },
    "radius_km": 5,
    "duration_min": 30,
    "include_categories": ["park", "waterfront"],
    "pet_friendly": true,
    "route_type": "loop"
  },
  "routes": [
    {
      "id": "r1",
      "summary": {
        "distance_km": 4.8,
        "duration_min": 42,
        "elevation_gain_m": 55,
        "match_score": 0.86,
        "crowd_score": 0.21,
        "pet_ratio": 0.82
      },
      "geometry": {
        "polyline": "u{~vF`pjoMdAfB... (encoded)",
        "bounds": { "south": 1.2870, "west": 103.7680, "north": 1.3010, "east": 103.7820 },
        "waypoints": [
          { "lat": 1.2901, "lng": 103.7702, "label": "start" }
        ]
      },
      "compliance": {
        "route_type": { "status": "satisfied", "note": "loop" },
        "pet_friendly": { "status": "satisfied", "note": "82% path dog=yes" }
      },
      "explain": ["Through 2 Parks and 1 waterfront"],
      "attribution": {
        "router": "ORS",
        "data_sources": ["OSM", "SRTM"],
        "disclaimer": "Agent congestion is based on POI density"
      }
    }
  ]
}
```

#### GET /api/v1/history
Retrieve user's trail search history.

**Response Example:**
```json
{
  "items": [
    {
      "ts": "2025-09-01T12:00:00Z",
      "constraints": {"...": "..."},
      "picked_route_id": "r2"
    }
  ]
}
```

## Configuration

### Environment Variables (.env)

```bash
# API Configuration
API_BASE_URL=https://api.mytrail.com

# Optional: API authentication
API_KEY=your_api_key_here
```

## Development

### Code Generation

When you modify Freezed models, regenerate code:

```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

### Testing

**Run all tests:**
```bash
flutter test
```

**Run widget tests:**
```bash
flutter test test/widget_test.dart
```

### Building

**Debug build:**
```bash
flutter build apk --debug
flutter build ios --debug
```

**Release build:**
```bash
flutter build apk --release
flutter build ios --release
```

## Key Features Implementation

### 🌈 Rainbow Animated Border
The input field features a custom `RainbowBorderPainter` with continuous color rotation:
- Uses `SweepGradient` with rainbow colors
- Animated with `AnimationController`
- Custom `CustomPainter` for smooth border rendering

### 🗺️ Real-time Map Updates
- Google Maps integration
- Dynamic route rendering
- Automatic bounds fitting when routes are selected
- Current location marker with custom styling

### 📱 Natural Language Processing
Input parsing extracts trail preferences from natural language:
- Category detection (park, waterfront, forest, mountain)
- Route type inference (loop, point-to-point)
- Pet-friendly detection
- Duration and distance preferences

### 📊 Route Visualization
- Horizontal scrollable route cards
- Real-time selection feedback
- Distance, duration, elevation metrics
- Loading states with shimmer effects

## Error Handling

- **Location Errors**: Permission handling with user-friendly messages
- **Network Errors**: Timeout, connectivity, and server error handling
- **API Errors**: Graceful degradation with retry mechanisms
- **Loading States**: Shimmer effects and progress indicators

## Performance Optimizations

- **State Management**: Efficient Riverpod providers
- **Map Rendering**: Optimized map rendering
- **Memory Management**: Proper disposal of controllers
- **Network Caching**: Dio interceptors for request optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the existing code style
4. Add tests for new features
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and feature requests, please use the GitHub issue tracker.
