"""Unit tests for the persisted route ranking service."""

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.route.ranking_service import RouteRankingService


def _base_route(route_id: str, *, safety: float, preference: float, crowd: float) -> dict:
    return {
        "id": route_id,
        "route_info": {
            "distance": 5000,
            "duration": "45m",
        },
        "waypoints": {
            "places": [
                {
                    "place_id": f"{route_id}_poi_1",
                    "name": "Sample Point",
                    "safety_level": "high" if safety > 0.75 else "medium",
                    "location": {"lat": 1.3, "lng": 103.8},
                },
                {
                    "place_id": f"{route_id}_poi_2",
                    "name": "Sample Point 2",
                    "safety_level": "medium" if safety > 0.5 else "low",
                    "location": {"lat": 1.31, "lng": 103.81},
                },
            ]
        },
        "metadata": {
            "safety_rating": safety,
            "preference_alignment": preference,
            "scenic_score": 0.65,
            "night_lighting": 0.6,
            "crowd_density": crowd,
            "bike_infrastructure": 0.7,
        },
    }


def test_rank_routes_uses_persisted_model():
    model_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "artifacts"
        / "route_ranking_model.json"
    )
    service = RouteRankingService(model_path=model_path, fallback_training=False)

    high_safety = _base_route("high", safety=0.92, preference=0.88, crowd=0.3)
    balanced = _base_route("balanced", safety=0.8, preference=0.75, crowd=0.45)
    risky = _base_route("risky", safety=0.55, preference=0.5, crowd=0.7)

    ranked = service.rank_routes([risky, balanced, high_safety])

    ordered_ids = [route["id"] for route in ranked]
    assert ordered_ids == ["high", "balanced", "risky"]

    for route in ranked:
        assert 0.0 <= route["final_score"] <= 1.0
        assert "predicted_score" in route.get("metadata", {})


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])