#!/usr/bin/env python3
"""
Test for feedback API endpoint
"""
import requests
import json
import sys
import os

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def test_feedback_api():
    """Test the feedback API endpoint"""
    base_url = "http://localhost:8000"
    
    # Test data matching your example
    test_feedback = [
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
                },
                {
                    "place_id": "ChIJLWy-d6cZ2jERxRto3g-f8vI",
                    "name": "Esplanade Park",
                    "category": "park",
                    "search_category": "nature",
                    "location": {
                        "lat": 1.289901,
                        "lng": 103.8538653,
                        "name": "Esplanade Park"
                    },
                    "rating": 4.6,
                    "distance_km": 1.05
                },
                {
                    "place_id": "ChIJnWdQKQQZ2jERScXuKeFHyIE",
                    "name": "ArtScience Museum",
                    "category": "attraction",
                    "search_category": "attraction",
                    "location": {
                        "lat": 1.2862738,
                        "lng": 103.8592663,
                        "name": "ArtScience Museum"
                    },
                    "rating": 4.4,
                    "distance_km": 0.36
                }
            ],
            "criteria": {
                "center": {"lat": 1.2834, "lng": 103.8607},
                "radius_km": 4.0,
                "duration_min": 30,
                "route_type": "loop",
                "include_categories": ["park", "attraction"],
                "avoid_categories": [],
                "pet_friendly": False
            }
        },
        {
            "id": "route_2",
            "selected": 0,
            "name": "Another route",
            "distance": 5000,
            "duration": "4000s",
            "waypoints": [],
            "criteria": {
                "center": {"lat": 1.2834, "lng": 103.8607},
                "radius_km": 4.0,
                "duration_min": 30,
                "route_type": "loop",
                "include_categories": ["park", "attraction"],
                "avoid_categories": [],
                "pet_friendly": False
            }
        }
    ]
    
    try:
        print("🧪 Testing feedback API...")
        print(f"📤 Sending data: {json.dumps(test_feedback, indent=2)}")
        
        response = requests.post(
            f"{base_url}/api/v1/feedback",
            json=test_feedback,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📥 Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Feedback API test passed!")
            return True
        else:
            print("❌ Feedback API test failed!")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on localhost:8000")
        print("💡 Start server with: conda run -n pract python app/main.py")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_feedback_api()
    sys.exit(0 if success else 1)
