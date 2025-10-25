# Route Generation Service

## 📋 Business Logic Overview

### `generate_candidate_routes` Function

Generates candidate routes from user criteria, returning fully populated route data and waypoint details.

#### 🔄 Processing Flow

1. **Search for Waypoint Candidates**
   - Search within `radius_km / 2` of the center
   - Target categories: `park`, `nature`, `attraction`, `restaurant`
   - Return up to 20 places per category

2. **Randomly Select Waypoints**
   - Choose 2–3 waypoints for each route
   - Preserve variety and exploration

3. **Build Concrete Routes**
   - Use the Google Routes API for navigation paths
   - Start and end at the same point (loop routes)
   - Traverse the selected waypoints

4. **Assemble Comprehensive Output**
   - Route geometry (polyline, distance, duration)
   - Detailed waypoint metadata (name, rating, category)
   - Additional metadata (search parameters, categories used)

#### 📊 Output Structure

```python
{
    'id': 'route_1',
    'route_info': {
        'overview_polyline': {'points': '...'},
        'duration': '5061s',
        'distance': 5956,  # meters
        'viewport': {...}
    },
    'waypoints': {
        'count': 3,
        'places': [
            {
                'name': 'Gardens by the Bay',
                'category': 'park',
                'search_category': 'park',
                'rating': 4.7,
                'distance_km': 0.46,
                'place_id': 'ChIJ...',
                # ... additional place details
            }
        ],
        'place_ids': ['ChIJ...', 'ChIJ...']
    },
    'metadata': {
        'center': (1.2834, 103.8607),
        'search_radius_km': 2.0,
        'route_type': 'loop',
        'categories_used': ['park', 'attraction', 'restaurant']
    },
    'criteria': {...}  # Original user criteria
}
```

#### 🎯 Core Capabilities

- **Smart Search**: Multi-category waypoint lookup within a sensible radius
- **Randomization**: Generate fresh waypoint combinations on each run
- **Completeness**: Include both navigation data and waypoint context
- **Traceability**: Preserve search parameters and original criteria
- **Resilience**: Gracefully handle API failures and edge cases

#### 🧪 Test Coverage

- **Happy Paths**: Marina Bay Sands, Singapore city center
- **Edge Cases**: Small search radius, remote coordinates
- **Error Handling**: API failures, no available places

#### 📈 Performance Notes

- **Search Efficiency**: Parallel lookups across categories
- **API Optimization**: Use Place IDs for precise routing
- **Data Fidelity**: One call returns full candidate details

## 🔧 Usage Example

```python
from app.services.route.generation_service import RouteGenerationService
from app.models.request import RouteCriteria, Center

# Create the service instance
service = RouteGenerationService()

# Define the search criteria
criteria = RouteCriteria(
    center=Center(lat=1.2834, lng=103.8607),
    radius_km=4.0,
    route_type="loop"
)

# Generate candidate routes
routes = await service.generate_candidate_routes(criteria, max_routes=3)

# Process the result set
for route in routes:
    print(f"Route {route['id']}: {route['route_info']['distance']}m")
    waypoints = [p['name'] for p in route['waypoints']['places']]
    print(f"Waypoints: {', '.join(waypoints)}")
```

## 🎉 Business Value

1. **User Experience**: Provide diverse route options
2. **Exploration**: Surface new points of interest and paths
3. **Practicality**: Bundle navigation and place insights
4. **Extensibility**: Easily add search types and filters

## 🧭 Offline Models: Route Clustering & Ranking

To increase diversity and ranking accuracy, the backend ships with two retrainable models:

1. **K-Means Clustering**: Groups routes into 5 clusters based on geography, distance, waypoint counts, etc., ensuring a varied recommendation list.
2. **Linear Regression Scoring**: Scores routes on distance, duration, safety, preference fit, night lighting, crowd levels, and more to drive ranking decisions.

### 📦 Unified Training Dataset

- Location: `backend/app/data/route_training_dataset.jsonl`
- Contents: 50 curated sample routes covering city commuting, nature walks, family outings, nightlife strolls, and coastal rides; each includes metadata and human labels.
- Extending Data: Append new routes to the JSONL file and rerun the training script.

### 🛠️ One-Command Training Script

`train_route_models.py` produces both the clustering and ranking models:

```bash
PYTHONPATH=backend python backend/app/scripts/train_route_models.py \
  --dataset backend/app/data/route_training_dataset.jsonl \
  --artifacts backend/app/artifacts \
  --clusters 5
```

The following files are created or updated:

- `backend/app/artifacts/route_cluster_model.json`
- `backend/app/artifacts/route_ranking_model.json`

For incremental training, add new samples and rerun the script; the models overwrite the previous versions.

### 🚀 Online Inference Flow

- **Clustering Service**: Loads the persisted K-Means model, writes `metadata['cluster_id']` for each candidate, and returns cluster summaries.
- **Ranking Service**: Loads the linear regression model, computes `final_score`, and orders routes accordingly.
- **Fallback Training**: When artifacts are missing and `fallback_training` is enabled, the services retrain from the latest dataset to keep production stable.
