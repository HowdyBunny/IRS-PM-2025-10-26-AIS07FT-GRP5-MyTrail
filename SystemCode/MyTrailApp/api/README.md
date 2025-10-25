# MyTrail NLP API Documentation

## API Endpoints

### POST `/api/v1/routes/query`

Generate route suggestions based on natural language queries.

### POST `/api/v1/feedback`

Submit user feedback for route selection to improve machine learning models.

## Request Format

```json
{
  "query": "I want a 1 hour loop route with parks and restaurants",
  "center": {
    "lat": 1.2834,
    "lng": 103.8607
  }
}
```

### Request Parameters

| Field        | Type   | Required | Description                                       |
| ------------ | ------ | -------- | ------------------------------------------------- |
| `query`      | String | ✅        | Natural language query (supports Chinese/English) |
| `center`     | Object | ✅        | Starting location coordinates                     |
| `center.lat` | Number | ✅        | Latitude                                          |
| `center.lng` | Number | ✅        | Longitude                                         |

### Supported Natural Language Expressions

#### **Place Type Recognition**
- **Parks**: "公园", "park", "绿地"
- **Restaurants**: "餐厅", "restaurant", "吃饭", "美食"
- **Cafes**: "咖啡", "cafe", "coffee"
- **Attractions**: "景点", "attraction", "旅游"
- **Nature**: "自然", "nature", "风景"

#### **Route Type Recognition**
- **Loop Routes**: "环形", "环线", "绕一圈", "loop", "circle"
- **Out and Back**: "往返", "来回", "out and back", "return"
- **Point to Point**: "点对点", "point to point", "直达"

#### **Duration Recognition**
- **Minutes**: "30分钟", "45min"
- **Hours**: "1小时", "2h", "2 hour"
- **Half hour**: "半小时"

#### **Distance Recognition**
- **Kilometers**: "2公里", "3km", "5千米"

### Query Examples

```
✅ "I want a 1 hour loop route with parks and restaurants"
✅ "Find me a 30min route with cafes and nature"
✅ "我想找一条1小时的环形路线，经过公园和餐厅"
✅ "帮我规划30分钟的跑步路线，要有自然风景"
✅ "2公里范围内找咖啡厅和景点的往返路线"
✅ "45分钟散步路线，经过公园"
```

## Response Format

```json
{
  "success": true,
  "message": "Successfully generated 5 routes",
  "routes": [
    {
      "id": "route_1",
      "name": "Via Supertree Grove Viewpoint, Esplanade Park +1 more",
      "distance": 6024,
      "duration": "5041s",
      "waypoints": [
        {
          "place_id": "ChIJkWHbygsZ2jERjkvNI-5be_8",
          "name": "Supertree Grove Viewpoint",
          "category": "park",
          "search_category": "nature",
          "location": {
            "lat": 1.281591,
            "lng": 103.8646819,
            "name": "Supertree Grove Viewpoint"
          },
          "rating": 4.8,
          "distance_km": 0.49
        }
      ],
      "geometry": {
        "overview_polyline": {
          "points": "encoded_polyline_string"
        },
        "viewport": {
          "low": {
            "latitude": 1.2816706,
            "longitude": 103.8546362
          },
          "high": {
            "latitude": 1.2912774,
            "longitude": 103.8648764
          }
        }
      },
      "metadata": {
        "center": [1.2834, 103.8607],
        "search_radius_km": 1.5,
        "route_type": "loop",
        "categories_used": ["attraction", "nature"]
      },
      "score": 0.8
    }
  ],
  "total_count": 5,
  "criteria": {
    "center": {"lat": 1.2834, "lng": 103.8607},
    "radius_km": 3.0,
    "duration_min": 60,
    "route_type": "loop",
    "include_categories": ["park", "restaurant"],
    "avoid_categories": [],
    "pet_friendly": false
  }
}
```

### Response Fields

#### Root Level

| Field         | Type    | Description                   |
| ------------- | ------- | ----------------------------- |
| `success`     | Boolean | Whether the request succeeded |
| `message`     | String  | Response message              |
| `routes`      | Array   | List of generated routes      |
| `total_count` | Number  | Total number of routes        |
| `criteria`    | Object  | User criteria for feedback training |

#### Route Object

| Field       | Type   | Description                           |
| ----------- | ------ | ------------------------------------- |
| `id`        | String | Unique route identifier               |
| `name`      | String | Route name (generated from waypoints) |
| `distance`  | Number | Total route distance (meters)         |
| `duration`  | String | Estimated duration (e.g., "5041s")    |
| `waypoints` | Array  | List of waypoints                     |
| `geometry`  | Object | Route geometry information            |
| `metadata`  | Object | Route metadata                        |
| `score`     | Number | Route score (0-1)                     |

#### Waypoint Object

| Field             | Type   | Description                             |
| ----------------- | ------ | --------------------------------------- |
| `place_id`        | String | Google Places ID                        |
| `name`            | String | Place name                              |
| `category`        | String | Standardized category                   |
| `search_category` | String | Category used for search                |
| `location`        | Object | Place coordinates                       |
| `rating`          | Number | Place rating                            |
| `distance_km`     | Number | Distance from center point (kilometers) |

#### Geometry Object

| Field                      | Type   | Description                    |
| -------------------------- | ------ | ------------------------------ |
| `overview_polyline`        | Object | Encoded route path             |
| `overview_polyline.points` | String | Google encoded polyline string |
| `viewport`                 | Object | Map display bounds             |
| `viewport.low`             | Object | Southwest corner coordinates   |
| `viewport.high`            | Object | Northeast corner coordinates   |

#### Metadata Object

| Field              | Type   | Description                    |
| ------------------ | ------ | ------------------------------ |
| `center`           | Array  | Search center point [lat, lng] |
| `search_radius_km` | Number | Actual search radius           |
| `route_type`       | String | Route type                     |
| `categories_used`  | Array  | Place categories actually used |

## NLP Processing Logic

### Default Values
- **Route Type**: `loop`
- **Search Radius**: `3.0` km
- **Expected Duration**: `60` minutes
- **Place Types**: `["park", "restaurant"]` (if no other types recognized)

### Parsing Priority
1. **Explicit numbers + units**: "30分钟" > "半小时"
2. **Specific place types**: "公园" > default types
3. **Explicit route types**: "往返" > default loop

## Example Files

- `nlp_request_example.json` - NLP API request format example
- `nlp_response_example.json` - NLP API response format example (includes 2 complete routes)
- `feedback_request_example.json` - Feedback API request format example
- `feedback_response_example.json` - Feedback API response format example

## Frontend Integration

### 1. API Call
```javascript
const response = await fetch('/api/v1/routes/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: "I want a 1 hour loop route with parks and restaurants",
    center: { lat: 1.2834, lng: 103.8607 }
  })
});
```

### 2. Map Integration
- **Polyline Decoding**: `overview_polyline.points` is a Google encoded polyline that needs to be decoded into coordinate points
- **Map Display**: Use `viewport` to set map display bounds
- **Route Rendering**: Decode polyline and draw route path on map
- **Waypoint Markers**: Use `waypoints` array to add markers on map

### 3. Development & Debugging
- Use `debug_nlp_frontend.html` for API testing
- Server address: `http://localhost:8000`
- Ensure backend service is running with CORS configured

## Error Response

```json
{
  "success": false,
  "message": "Route generation failed: error details",
  "routes": [],
  "total_count": 0
}
```

## Technical Implementation

### NLP Processing Pipeline
1. **Text Preprocessing**: Convert to lowercase, extract keywords
2. **Entity Recognition**: Identify place types, duration, distance, route type
3. **Parameter Mapping**: Map recognized entities to `RouteCriteria` object
4. **Route Generation**: Call route generation service
5. **Response Building**: Return standardized route response

### Supported Languages
- **Chinese**: Full support for Chinese keywords and expressions
- **English**: Support for English keywords and common expressions
- **Mixed**: Support for mixed Chinese-English queries

## Feedback API

### POST `/api/v1/feedback`

Submit user feedback for route selection to improve machine learning models.

#### Request Format

```json
[
  {
    "id": "route_1",
    "selected": 1,
    "name": "Via Supertree Grove Viewpoint, Esplanade Park +1 more",
    "distance": 6024,
    "duration": "5041s",
    "waypoints": [
      {
        "place_id": "ChIJkWHbygsZ2jERjkvNI-5be_8",
        "name": "Supertree Grove Viewpoint",
        "category": "park",
        "search_category": "nature",
        "location": {
          "lat": 1.281591,
          "lng": 103.8646819,
          "name": "Supertree Grove Viewpoint"
        },
        "rating": 4.8,
        "distance_km": 0.49
      }
    ],
    "score": 0.8,
    "criteria": {
      "center": {"lat": 1.2834, "lng": 103.8607},
      "radius_km": 3.0,
      "duration_min": 60,
      "route_type": "loop",
      "include_categories": ["park", "restaurant"],
      "avoid_categories": [],
      "pet_friendly": false
    }
  },
  {
    "id": "route_2",
    "selected": 0,
    "name": "Another route",
    "distance": 5000,
    "duration": "4000s",
    "waypoints": [],
    "score": 0.6,
    "criteria": {
      "center": {"lat": 1.2834, "lng": 103.8607},
      "radius_km": 3.0,
      "duration_min": 60,
      "route_type": "loop",
      "include_categories": ["park", "restaurant"],
      "avoid_categories": [],
      "pet_friendly": false
    }
  }
]
```

#### Request Parameters

| Field        | Type   | Required | Description                                       |
| ------------ | ------ | -------- | ------------------------------------------------- |
| `id`         | String | ✅        | Route identifier                                  |
| `selected`   | Number | ✅        | 1 for selected, 0 for not selected               |
| `name`       | String | ✅        | Route name                                        |
| `distance`   | Number | ✅        | Route distance in meters                          |
| `duration`   | String | ✅        | Route duration (e.g., "5041s")                   |
| `waypoints`  | Array  | ✅        | List of waypoints                                 |
| `score`      | Number | ✅        | Route score (0-1)                                 |
| `criteria`   | Object | ✅        | User criteria used for route generation           |

#### Response Format

```json
{
  "status": "success",
  "message": "Feedback stored successfully"
}
```

#### Error Response

```json
{
  "status": "error",
  "message": "Feedback submission failed: error details"
}
```

### Frontend Integration for Feedback

```javascript
// Submit user feedback
const feedbackData = routes.map(route => ({
  id: route.id,
  selected: route.userSelected ? 1 : 2,  // 1=selected, 2=not selected
  name: route.name,
  distance: route.distance,
  duration: route.duration,
  waypoints: route.waypoints,
  score: route.score,
  criteria: route.criteria  // From the original API response
}));

const response = await fetch('/api/v1/feedback', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(feedbackData)
});
```

### Data Storage

- Feedback data is stored in SQLite database (`feedback.db`)
- Data includes user selections, route details, and criteria
- Used for machine learning model training and improvement
- Export tools available for data analysis