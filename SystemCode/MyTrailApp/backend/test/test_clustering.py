"""Unit tests for the persisted route clustering service."""

from pathlib import Path
import sys
from typing import List, Tuple

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.route.clustering_service import RouteClusteringService


def _mock_route(
    route_id: str, distance: int, duration: str, coords: List[Tuple[float, float]]
):
    places = [
        {
            "place_id": f"{route_id}_place_{idx}",
            "name": f"Waypoint {idx}",
            "category": "park",
            "search_category": "park",
            "location": {"lat": lat, "lng": lng},
        }
        for idx, (lat, lng) in enumerate(coords)
    ]
    return {
        "id": route_id,
        "route_info": {"distance": distance, "duration": duration},
        "waypoints": {"places": places},
        "metadata": {},
    }


def test_cluster_routes_uses_trained_model():
    model_path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "artifacts"
        / "route_clustering_model.json"
    )
    service = RouteClusteringService(model_path=model_path, fallback_training=False)

    routes = [
        _mock_route(
            "short_route",
            1700,
            "600s",
            [(1.2855, 103.834), (1.2865, 103.836)],
        ),
        _mock_route(
            "medium_route",
            5500,
            "2050s",
            [
                (1.336, 103.9075),
                (1.338, 103.9095),
                (1.335, 103.906),
            ],
        ),
        _mock_route(
            "long_route",
            10300,
            "3900s",
            [
                (1.412, 103.985),
                (1.414, 103.987),
                (1.413, 103.986),
                (1.411, 103.983),
            ],
        ),
    ]

    result = service.cluster_routes(routes)

    assert len(result["clusters"]) == 5
    assert sum(cluster["size"] for cluster in result["clusters"]) == len(routes)

    assignments = {route["id"]: route["metadata"]["cluster_id"] for route in routes}
    assert set(assignments.values()).issubset({0, 1, 2, 3, 4})

    for cluster in result["clusters"]:
        assert cluster["cluster_id"] in {0, 1, 2, 3, 4}
        if cluster["size"]:
            for route_id in cluster["route_ids"]:
                assert assignments[route_id] == cluster["cluster_id"]


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])