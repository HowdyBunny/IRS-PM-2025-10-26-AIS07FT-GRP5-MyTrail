CANON_CATEGORIES = {
    "park": {"park", "parks", "green", "greenway", "garden", "gardens"},
    "waterfront": {"waterfront", "harbor", "seafront"},
    "restaurant": {"restaurant", "restaurants", "food", "dining"},
    "shopping": {"mall","shopping","shops"},
    "museum": {"museum","museums"},
    "trail": {"trail","trails","hiking"},
    "river": {"river","riverside"},
    "lake": {"lake","lakeside"},
    "garden": {"garden","gardens","botanical"},
    "viewpoint": {"viewpoint","scenic","overlook"},
    "highway": {"highway","highways","motorway"}
}
CANON_LOOKUP = {w:canon for canon, syns in CANON_CATEGORIES.items() for w in syns}

ROUTE_TYPE_MAP = {
    "loop": {"loop","circular","round","roundtrip","round-trip"},
    "out-and-back": {"out-and-back","out and back","return the same way","there and back"}
}
