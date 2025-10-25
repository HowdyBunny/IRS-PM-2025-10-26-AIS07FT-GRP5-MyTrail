import json

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def compute_score(route):
    waypoints = route.get("waypoints", [])
    distance_m = route.get("distance", 0)
    metadata = route.get("metadata", {})

    # ---- 1. Average rating ----
    ratings = [wp.get("rating", 0) for wp in waypoints if isinstance(wp.get("rating"), (int, float))]
    rating_score = clamp(sum(ratings) / len(ratings) / 5.0, 0, 1) if ratings else 0.5

    # ---- 2. Route length preference (3–7 km ideal) ----
    km = distance_m / 1000.0
    if km < 3:
        length_score = (km - 1) / 2 if km > 1 else 0
    elif km <= 7:
        length_score = 1
    elif km < 12:
        length_score = (12 - km) / 5
    else:
        length_score = 0
    length_score = clamp(length_score)

    # ---- 3. Category diversity ----
    cats = { (wp.get("search_category") or wp.get("category") or "").lower() for wp in waypoints }
    diversity_score = clamp(len(cats) / 4.0)

    # ---- 4. Scenic bonus ----
    scenic_bonus = 1.0 if any((wp.get("search_category") or "").lower() in ["nature", "park", "water"] for wp in waypoints) else 0.0

    # ---- 5. Loop bonus ----
    loop_bonus = 1.0 if metadata.get("route_type", "").lower() == "loop" else 0.0

    # ---- 6. Overall score (extra weight for search_category) ----
    # Weights: rating 0.15, length 0.15, diversity 0.10, scenic 0.40, loop 0.20
    score = (
        0.15 * rating_score +
        0.15 * length_score +
        0.10 * diversity_score +
        0.40 * scenic_bonus +
        0.20 * loop_bonus
    )
    return round(clamp(score), 4)

def main():
    input_file = "data/synthetic_data.json"
    output_file = "data/synthetic_data_scored.json"

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Supports two structures: a list or {"routes": [...]}
    if isinstance(data, dict) and "routes" in data:
        routes = data["routes"]
        for r in routes:
            r["score"] = compute_score(r)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({"routes": routes}, f, ensure_ascii=False, indent=2)
    elif isinstance(data, list):
        for r in data:
            r["score"] = compute_score(r)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        print("❌ Invalid JSON format; expected a list or an object containing a 'routes' key")

    print("✅ Scoring complete; results saved to:", output_file)

if __name__ == "__main__":
    main()
