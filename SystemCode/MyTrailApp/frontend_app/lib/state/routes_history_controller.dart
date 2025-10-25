import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../data/models/route.dart';

final routeHistoryControllerProvider =
    ChangeNotifierProvider<RouteHistoryController>((ref) {
  return RouteHistoryController();
});

class RouteHistoryController extends ChangeNotifier {
  RouteHistoryController() {
    _init();
  }

  static const String _storageKey = 'route_history_sessions_v1';
  static const int _maxSessions = 10;

  final List<RouteHistorySession> _sessions = [];
  final Completer<void> _ready = Completer<void>();
  SharedPreferences? _prefs;

  List<RouteHistorySession> get sessions => List.unmodifiable(_sessions);

  Future<void> _init() async {
    try {
      _prefs = await SharedPreferences.getInstance();
      final stored = _prefs?.getStringList(_storageKey) ?? const <String>[];
      final decoded = <RouteHistorySession>[];
      for (final item in stored) {
        try {
          final map = jsonDecode(item) as Map<String, dynamic>;
          decoded.add(RouteHistorySession.fromJson(map));
        } catch (error, stackTrace) {
          if (kDebugMode) {
            debugPrint('Failed to decode route history item: $error');
            debugPrint(stackTrace.toString());
          }
        }
      }
      _sessions
        ..clear()
        ..addAll(decoded);
    } finally {
      if (!_ready.isCompleted) {
        _ready.complete();
      }
      notifyListeners();
    }
  }

  RouteHistorySession? sessionById(String id) {
    for (final session in _sessions) {
      if (session.id == id) {
        return session;
      }
    }
    return null;
  }

  Future<void> recordSearchResult({
    required Iterable<MtRoute> routes,
    RouteHistorySearchCenter? center,
    int? totalCount,
    DateTime? timestamp,
    String? query,
  }) async {
    await _ready.future;
    final routeList = routes.toList(growable: false);
    if (routeList.isEmpty) {
      return;
    }

    final createdAt = (timestamp ?? DateTime.now()).toUtc();
    final session = RouteHistorySession(
      id: createdAt.microsecondsSinceEpoch.toString(),
      timestamp: createdAt,
      center: center,
      totalCount: totalCount,
      query: query,
      routes: routeList
          .map(RouteHistoryRoute.fromMtRoute)
          .toList(growable: false),
    );

    _sessions.insert(0, session);
    if (_sessions.length > _maxSessions) {
      _sessions.removeRange(_maxSessions, _sessions.length);
    }
    await _persist();
    notifyListeners();
  }

  Future<void> clear() async {
    await _ready.future;
    _sessions.clear();
    await _prefs?.remove(_storageKey);
    notifyListeners();
  }

  Future<void> _persist() async {
    final encoded = _sessions
        .map((session) => jsonEncode(session.toJson()))
        .toList(growable: false);
    await _prefs?.setStringList(_storageKey, encoded);
  }
}

class RouteHistorySession {
  RouteHistorySession({
    required this.id,
    required this.timestamp,
    required this.routes,
    this.center,
    this.totalCount,
    this.query,
  });

  final String id;
  final DateTime timestamp;
  final List<RouteHistoryRoute> routes;
  final RouteHistorySearchCenter? center;
  final int? totalCount;
  final String? query;

  Map<String, dynamic> toJson() => {
        'id': id,
        'timestamp': timestamp.toIso8601String(),
        'routes': routes.map((route) => route.toJson()).toList(),
        'center': center?.toJson(),
        'total_count': totalCount,
        'query': query,
      };

  factory RouteHistorySession.fromJson(Map<String, dynamic> json) {
    final routesJson = json['routes'] as List<dynamic>? ?? const [];
    return RouteHistorySession(
      id: json['id'] as String? ??
          DateTime.now().microsecondsSinceEpoch.toString(),
      timestamp: DateTime.tryParse(json['timestamp'] as String? ?? '')
              ?.toUtc() ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      routes: routesJson
          .map((item) => RouteHistoryRoute.fromJson(
                (item as Map).cast<String, dynamic>(),
              ))
          .toList(growable: false),
      center: json['center'] == null
          ? null
          : RouteHistorySearchCenter.fromJson(
              (json['center'] as Map).cast<String, dynamic>(),
            ),
      totalCount: json['total_count'] as int?,
      query: json['query'] as String?,
    );
  }

  List<MtRoute> toMtRoutes() =>
      routes.map((route) => route.toMtRoute()).toList(growable: false);

  RouteHistoryRoute? routeById(String routeId) {
    for (final route in routes) {
      if (route.id == routeId) {
        return route;
      }
    }
    return null;
  }
}

class RouteHistoryRoute {
  RouteHistoryRoute({required this.payload});

  final Map<String, dynamic> payload;

  String get id => payload['id'] as String? ?? '';

  Map<String, dynamic> toJson() => payload;

  MtRoute toMtRoute() => MtRoute.fromJson(payload);

  factory RouteHistoryRoute.fromJson(Map<String, dynamic> json) {
    return RouteHistoryRoute(payload: json);
  }

  factory RouteHistoryRoute.fromMtRoute(MtRoute route) {
    return RouteHistoryRoute(payload: route.toJson());
  }
}

class RouteHistorySearchCenter {
  const RouteHistorySearchCenter({
    required this.lat,
    required this.lng,
  });

  final double lat;
  final double lng;

  Map<String, dynamic> toJson() => {
        'lat': lat,
        'lng': lng,
      };

  factory RouteHistorySearchCenter.fromJson(Map<String, dynamic> json) {
    return RouteHistorySearchCenter(
      lat: (json['lat'] as num?)?.toDouble() ?? 0,
      lng: (json['lng'] as num?)?.toDouble() ?? 0,
    );
  }
}
