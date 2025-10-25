class RouteResponse {
  RouteResponse({
    required this.success,
    required this.message,
    required this.routes,
    required this.totalCount,
  });

  final bool success;
  final String message;
  final List<MtRoute> routes;
  final int totalCount;

  factory RouteResponse.fromJson(Map<String, dynamic> json) {
    final routesJson = json['routes'] as List<dynamic>?;
    return RouteResponse(
      success: json['success'] as bool? ?? false,
      message: json['message'] as String? ?? '',
      routes: routesJson == null
          ? <MtRoute>[]
          : routesJson
              .map((routeJson) =>
                  MtRoute.fromJson(routeJson as Map<String, dynamic>))
              .toList(),
      totalCount: json['total_count'] as int? ??
          (routesJson?.length ?? 0),
    );
  }

  Map<String, dynamic> toJson() => {
        'success': success,
        'message': message,
        'routes': routes.map((route) => route.toJson()).toList(),
        'total_count': totalCount,
      };
}

class MtRoute {
  MtRoute({
    required this.id,
    required this.name,
    required this.distance,
    required this.duration,
    required this.waypoints,
    required this.geometry,
    required this.metadata,
    required this.score,
  });

  final String id;
  final String name;
  final int distance; // meters
  final String duration; // e.g. "5876s"
  final List<Waypoint> waypoints;
  final RouteGeometry geometry;
  final RouteMetadata metadata;
  final double score;

  factory MtRoute.fromJson(Map<String, dynamic> json) {
    final waypointsJson = json['waypoints'] as List<dynamic>?;
    return MtRoute(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      distance: json['distance'] as int? ?? 0,
      duration: json['duration'] as String? ?? '0s',
      waypoints: waypointsJson == null
          ? <Waypoint>[]
          : waypointsJson
              .map((wpJson) =>
                  Waypoint.fromJson(wpJson as Map<String, dynamic>))
              .toList(),
      geometry: RouteGeometry.fromJson(
        json['geometry'] as Map<String, dynamic>? ?? const {},
      ),
      metadata: RouteMetadata.fromJson(
        json['metadata'] as Map<String, dynamic>? ?? const {},
      ),
      score: (json['score'] as num?)?.toDouble() ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'distance': distance,
        'duration': duration,
        'waypoints': waypoints.map((wp) => wp.toJson()).toList(),
        'geometry': geometry.toJson(),
        'metadata': metadata.toJson(),
        'score': score,
      };
}

class Waypoint {
  Waypoint({
    required this.placeId,
    required this.name,
    required this.category,
    required this.searchCategory,
    required this.location,
    this.rating,
    this.distanceKm,
  });

  final String placeId;
  final String name;
  final String category;
  final String searchCategory;
  final WaypointLocation location;
  final double? rating;
  final double? distanceKm;

  factory Waypoint.fromJson(Map<String, dynamic> json) {
    return Waypoint(
      placeId: json['place_id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      category: json['category'] as String? ?? 'unknown',
      searchCategory: json['search_category'] as String? ?? 'unknown',
      location: WaypointLocation.fromJson(
        json['location'] as Map<String, dynamic>? ?? const {},
      ),
      rating: (json['rating'] as num?)?.toDouble(),
      distanceKm: (json['distance_km'] as num?)?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {
        'place_id': placeId,
        'name': name,
        'category': category,
        'search_category': searchCategory,
        'location': location.toJson(),
        'rating': rating,
        'distance_km': distanceKm,
      };
}

class WaypointLocation {
  WaypointLocation({
    required this.lat,
    required this.lng,
    this.name,
  });

  final double lat;
  final double lng;
  final String? name;

  factory WaypointLocation.fromJson(Map<String, dynamic> json) {
    return WaypointLocation(
      lat: (json['lat'] as num?)?.toDouble() ?? 0,
      lng: (json['lng'] as num?)?.toDouble() ?? 0,
      name: json['name'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'lat': lat,
        'lng': lng,
        'name': name,
      };
}

class RouteGeometry {
  RouteGeometry({
    required this.overviewPolyline,
    required this.viewport,
  });

  final OverviewPolyline overviewPolyline;
  final Viewport viewport;

  factory RouteGeometry.fromJson(Map<String, dynamic> json) {
    return RouteGeometry(
      overviewPolyline: OverviewPolyline.fromJson(
        json['overview_polyline'] as Map<String, dynamic>? ?? const {},
      ),
      viewport: Viewport.fromJson(
        json['viewport'] as Map<String, dynamic>? ?? const {},
      ),
    );
  }

  Map<String, dynamic> toJson() => {
        'overview_polyline': overviewPolyline.toJson(),
        'viewport': viewport.toJson(),
      };
}

class OverviewPolyline {
  OverviewPolyline({required this.points});

  final String points;

  factory OverviewPolyline.fromJson(Map<String, dynamic> json) {
    return OverviewPolyline(points: json['points'] as String? ?? '');
  }

  Map<String, dynamic> toJson() => {
        'points': points,
      };
}

class Viewport {
  const Viewport({
    required this.low,
    required this.high,
  });

  final ViewportPoint low;
  final ViewportPoint high;

  factory Viewport.fromJson(Map<String, dynamic> json) {
    return Viewport(
      low: ViewportPoint.fromJson(
        json['low'] as Map<String, dynamic>? ?? const {},
      ),
      high: ViewportPoint.fromJson(
        json['high'] as Map<String, dynamic>? ?? const {},
      ),
    );
  }

  Map<String, dynamic> toJson() => {
        'low': low.toJson(),
        'high': high.toJson(),
      };
}

class ViewportPoint {
  const ViewportPoint({
    required this.lat,
    required this.lng,
  });

  final double lat;
  final double lng;

  factory ViewportPoint.fromJson(Map<String, dynamic> json) {
    return ViewportPoint(
      lat: (json['latitude'] as num?)?.toDouble() ?? 0,
      lng: (json['longitude'] as num?)?.toDouble() ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'latitude': lat,
        'longitude': lng,
      };
}

class RouteMetadata {
  RouteMetadata({
    required this.center,
    required this.searchRadiusKm,
    required this.routeType,
    required this.categoriesUsed,
  });

  final List<double> center;
  final double? searchRadiusKm;
  final String? routeType;
  final List<String>? categoriesUsed;

  factory RouteMetadata.fromJson(Map<String, dynamic> json) {
    final centerList = json['center'] as List<dynamic>?;
    return RouteMetadata(
      center: centerList == null
          ? const <double>[]
          : centerList
              .map((value) => (value as num?)?.toDouble() ?? 0)
              .toList(),
      searchRadiusKm:
          (json['search_radius_km'] as num?)?.toDouble(),
      routeType: json['route_type'] as String?,
      categoriesUsed: (json['categories_used'] as List<dynamic>?)
          ?.map((value) => value as String)
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'center': center,
        'search_radius_km': searchRadiusKm,
        'route_type': routeType,
        'categories_used': categoriesUsed,
      };
}
