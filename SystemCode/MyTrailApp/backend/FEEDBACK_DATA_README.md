# Feedback Data Storage Guide

## Data Storage

### Database Location
- **File**: `backend/feedback.db`
- **Type**: SQLite database
- **Auto-created**: When first feedback is submitted

### Database Schema
```sql
CREATE TABLE route_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id TEXT NOT NULL,
    selected INTEGER NOT NULL,        -- 1=selected, 2=not selected
    name TEXT NOT NULL,
    distance INTEGER NOT NULL,
    duration TEXT NOT NULL,
    waypoints_json TEXT NOT NULL,
    criteria_json TEXT,
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Data Export

### Export Script (Recommended)
```bash
cd backend/test
python export_feedback_data.py
```

**Generated Files**:
- `feedback_data.json` - Complete data with waypoints
- `feedback_data.csv` - Tabular format for ML training

### Direct Database Access
```python
import sqlite3

conn = sqlite3.connect('feedback.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM route_feedback")
data = cursor.fetchall()
conn.close()
```

## Data Format

### Training Data (CSV)
| route_id | selected | distance | duration_seconds | waypoint_count | avg_rating | category_diversity |
|----------|----------|----------|------------------|----------------|------------|-------------------|
| route_1  | 1        | 6024     | 5041             | 3              | 4.6        | 0.67              |

### Features for ML
- `distance`: Route distance in meters
- `duration_seconds`: Route duration in seconds
- `waypoint_count`: Number of waypoints
- `avg_rating`: Average waypoint rating
- `category_diversity`: Category diversity ratio
- `selected`: Target variable (1=selected, 2=not selected)

## Testing

### Run Tests
```bash
# Start server
cd backend
conda run -n pract python app/main.py

# Run tests (new terminal)
cd backend/test
python test_feedback_api.py
```

### Test Data
- 2 route feedbacks
- 1 selected (selected=1)
- 1 not selected (selected=2)
- Complete waypoint information
