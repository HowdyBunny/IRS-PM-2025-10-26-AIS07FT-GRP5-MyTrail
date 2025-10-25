from __future__ import annotations

from typing import Dict, List, Tuple


def optimize_waypoint_order_by_two_opt(waypoints: List[Dict]) -> List[Dict]:
    """
    Apply a 2-opt style heuristic to remove line intersections from an open path.

    The algorithm repeatedly searches for intersecting edges and reverses the
    intermediate segment until no intersections remain. This prioritises removing
    crossings over minimising total distance.
    """
    if len(waypoints) < 4:
        # Fewer than four points cannot produce intersecting non-adjacent edges.
        return waypoints

    optimized = waypoints[:]
    improved = True

    while improved:
        improved = False

        for i in range(len(optimized) - 3):
            for j in range(i + 2, len(optimized) - 1):
                p1 = _extract_point(optimized[i])
                p2 = _extract_point(optimized[i + 1])
                p3 = _extract_point(optimized[j])
                p4 = _extract_point(optimized[j + 1])

                if _segments_intersect(p1, p2, p3, p4):
                    # Reverse the segment between i+1 and j (inclusive) to remove the crossing.
                    optimized[i + 1 : j + 1] = reversed(optimized[i + 1 : j + 1])
                    improved = True
                    break

            if improved:
                break

    return optimized


def _extract_point(waypoint: Dict) -> Tuple[float, float]:
    location = waypoint.get("location", {})
    return location.get("lat"), location.get("lng")


def _segments_intersect(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float],
) -> bool:
    """Return True if segment p1-p2 intersects with segment p3-p4."""
    o1 = _orientation(p1, p2, p3)
    o2 = _orientation(p1, p2, p4)
    o3 = _orientation(p3, p4, p1)
    o4 = _orientation(p3, p4, p2)

    # Proper intersection
    if o1 != o2 and o3 != o4:
        return True

    # Handle collinear cases
    if o1 == 0 and _on_segment(p1, p3, p2):
        return True
    if o2 == 0 and _on_segment(p1, p4, p2):
        return True
    if o3 == 0 and _on_segment(p3, p1, p4):
        return True
    if o4 == 0 and _on_segment(p3, p2, p4):
        return True

    return False


def _orientation(
    a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]
) -> int:
    """Return orientation of ordered triplet (a, b, c).

    Returns:
        0 if collinear
        1 if clockwise
        2 if counter-clockwise
    """
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    val = (by - ay) * (cx - bx) - (bx - ax) * (cy - by)
    if abs(val) < 1e-12:
        return 0
    return 1 if val > 0 else 2


def _on_segment(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
) -> bool:
    """Return True if b lies on segment ac."""
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    return (
        min(ax, cx) - 1e-12 <= bx <= max(ax, cx) + 1e-12
        and min(ay, cy) - 1e-12 <= by <= max(ay, cy) + 1e-12
    )

