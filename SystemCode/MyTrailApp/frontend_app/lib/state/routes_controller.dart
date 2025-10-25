import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';

import '../data/models/route.dart';
import '../services/routes_api.dart';
import 'routes_history_controller.dart';

/// Toggle for loading mock data instead of hitting the network.
const bool useMockRoutes = bool.fromEnvironment(
  'USE_MOCK_ROUTES',
  defaultValue: false,
);

/// Provides a configured Dio instance for the routes API.
final dioProvider = Provider<Dio>((ref) {
  final options = BaseOptions(
    baseUrl: const String.fromEnvironment(
      'API_BASE_URL',
      // defaultValue: 'http://0.0.0.0:8000',
      defaultValue: 'http://192.168.0.207:8000',
    ),
    connectTimeout: const Duration(seconds: 10),
    sendTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 20),
    contentType: Headers.jsonContentType,
    responseType: ResponseType.json,
    headers: const {
      Headers.acceptHeader: Headers.jsonContentType,
    },
  );

  final dio = Dio(options);
  dio.interceptors.add(LogInterceptor(requestBody: true, responseBody: false));
  return dio;
});

/// Provides the routes API client.
final routesApiProvider = Provider<RoutesApi>((ref) {
  final dio = ref.watch(dioProvider);
  return RoutesApi(dio);
});

/// Change notifier provider bridging the routes controller to the UI.
final routesControllerProvider = ChangeNotifierProvider<RoutesController>((
  ref,
) {
  final api = ref.watch(routesApiProvider);
  return RoutesController(api: api, ref: ref);
});

class RoutesController extends ChangeNotifier {
  RoutesController({required RoutesApi api, required Ref ref})
      : _api = api,
        _ref = ref;

  final RoutesApi _api;
  final Ref _ref;
  final List<MtRoute> _routes = [];
  final Set<String> _hiddenCategories = <String>{};

  LatLng? _center;
  MtRoute? _selected;
  MtRoute? _activeRoute;
  bool _loading = false;
  bool _startingRoute = false;
  String? _error;
  String? _startError;
  int _totalCount = 0;
  String? _lastQuery;

  List<MtRoute> get routes => List.unmodifiable(_routes);
  MtRoute? get selected => _selected;
  MtRoute? get activeRoute => _activeRoute;
  bool get loading => _loading;
  bool get startingRoute => _startingRoute;
  String? get error => _error;
  String? get startError => _startError;
  LatLng? get center => _center;
  int get totalCount => _totalCount;
  Set<String> get hiddenCategories => Set.unmodifiable(_hiddenCategories);
  String? get lastQuery => _lastQuery;

  bool get hasActiveRoute => _activeRoute != null;

  bool isCategoryVisible(String category) =>
      !_hiddenCategories.contains(category.toLowerCase());

  Future<void> loadRoutes({
    required String query,
    required LatLng center,
  }) async {
    _loading = true;
    _error = null;
    _center = center;
    _lastQuery = query;
    _activeRoute = null;
    _startError = null;
    notifyListeners();

    try {
      final response = useMockRoutes
          ? await _loadMockRoutes()
          : await _api.fetchRoutes(
              query: query,
              lat: center.latitude,
              lng: center.longitude,
            );

      _routes
        ..clear()
        ..addAll(response.routes);
      _hiddenCategories.clear();
      _totalCount = response.totalCount;
      _selected = _routes.isEmpty ? null : _routes.first;
      _activeRoute = null;
      _startError = null;

      await _ref.read(routeHistoryControllerProvider).recordSearchResult(
            routes: response.routes,
            center: RouteHistorySearchCenter(
              lat: center.latitude,
              lng: center.longitude,
            ),
            totalCount: response.totalCount,
            query: query,
          );
    } on RoutesException catch (error, stackTrace) {
      _error = error.message;
      if (kDebugMode) {
        debugPrint('RoutesException: ${error.message}\n$stackTrace');
      }
    } catch (error, stackTrace) {
      _error = 'Unable to connect to the server. Please check your connection.';
      if (kDebugMode) {
        debugPrint('Unexpected error loading routes: $error\n$stackTrace');
      }
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  void selectRoute(MtRoute route) {
    if (_selected == route) {
      return;
    }
    if (!_routes.contains(route)) {
      return;
    }
    _startError = null;
    _selected = route;
    notifyListeners();
  }

  void clear() {
    _routes.clear();
    _selected = null;
    _activeRoute = null;
    _center = null;
    _error = null;
    _startError = null;
    _totalCount = 0;
    _lastQuery = null;
    _startingRoute = false;
    _hiddenCategories.clear();
    notifyListeners();
  }

  void dismissError() {
    if (_error == null) {
      return;
    }
    _error = null;
    notifyListeners();
  }

  void toggleCategoryVisibility(String category) {
    final key = category.toLowerCase();
    if (_hiddenCategories.contains(key)) {
      _hiddenCategories.remove(key);
    } else {
      _hiddenCategories.add(key);
    }
    notifyListeners();
  }

  Iterable<Waypoint> allWaypoints() sync* {
    final seen = <String>{};
    for (final route in _routes) {
      for (final waypoint in route.waypoints) {
        if (seen.add(waypoint.placeId)) {
          yield waypoint;
        }
      }
    }
  }

  void displayHistorySession(
    RouteHistorySession session, {
    String? routeId,
  }) {
    final restored = session.toMtRoutes();
    if (restored.isEmpty) {
      return;
    }

    _loading = false;
    _error = null;
    _hiddenCategories.clear();

    _routes
      ..clear()
      ..addAll(restored);

    final fallbackSelected = _routes.first;
    final selectedRoute = routeId == null
        ? fallbackSelected
        : _routes.firstWhere(
            (route) => route.id == routeId,
            orElse: () => fallbackSelected,
          );

    _selected = selectedRoute;
    _activeRoute = null;
    _startError = null;
    _totalCount = session.totalCount ?? _routes.length;
    _lastQuery = session.query;

    final resolvedCenter = _resolveCenterForHistory(session, selectedRoute);
    if (resolvedCenter != null) {
      _center = resolvedCenter;
    }

    notifyListeners();
  }

  LatLng? _resolveCenterForHistory(
    RouteHistorySession session,
    MtRoute selected,
  ) {
    final stored = session.center;
    if (stored != null) {
      return LatLng(stored.lat, stored.lng);
    }

    final metadataCenter = selected.metadata.center;
    if (metadataCenter.length >= 2) {
      return LatLng(metadataCenter[0], metadataCenter[1]);
    }

    if (selected.waypoints.isNotEmpty) {
      final first = selected.waypoints.first;
      return LatLng(first.location.lat, first.location.lng);
    }

    return null;
  }

  Future<String?> startRoute({
    MtRoute? route,
    String? criteria,
  }) async {
    final target = route ?? _selected;
    if (target == null) {
      return 'No route selected.';
    }
    if (_startingRoute) {
      return null;
    }

    _startingRoute = true;
    _startError = null;
    notifyListeners();

    final currentCriteria = (criteria ?? _lastQuery)?.trim();
    final criteriaPayload = (currentCriteria != null && currentCriteria.isNotEmpty)
        ? <String, dynamic>{'query': currentCriteria}
        : const <String, dynamic>{};
    final payload = _routes
        .map(
          (item) => _buildFeedbackPayload(
            item,
            selectedRouteId: target.id,
            criteria: criteriaPayload,
          ),
        )
        .toList(growable: false);

    String? errorMessage;
    try {
      await _api.submitFeedback(payload);
      _activeRoute = target;
      _selected = target;
    } on RoutesException catch (error) {
      errorMessage = error.message;
    } catch (error) {
      errorMessage = 'Failed to start the route. Please try again.';
    } finally {
      _startingRoute = false;
      _startError = errorMessage;
      notifyListeners();
    }

    return errorMessage;
  }

  void resetActiveRoute() {
    if (_activeRoute == null) {
      return;
    }
    _activeRoute = null;
    _startError = null;
    notifyListeners();
  }

  Map<String, dynamic> _buildFeedbackPayload(
    MtRoute route, {
    required String selectedRouteId,
    Map<String, dynamic>? criteria,
  }) {
    return {
      'id': route.id,
      'selected': route.id == selectedRouteId ? 1 : 0,
      'criteria': criteria ?? const <String, dynamic>{},
      'name': route.name,
      'distance': route.distance,
      'duration': route.duration,
      'score': route.score,
      'waypoints': route.waypoints
          .map(
            (waypoint) => {
              'place_id': waypoint.placeId,
              'name': waypoint.name,
              'category': waypoint.category,
              'search_category': waypoint.searchCategory,
              'location': {
                'lat': waypoint.location.lat,
                'lng': waypoint.location.lng,
                'name': waypoint.location.name,
              },
              'rating': waypoint.rating,
              'distance_km': waypoint.distanceKm,
            },
          )
          .toList(growable: false),
    };
  }

  Future<RouteResponse> _loadMockRoutes() async {
    await Future<void>.delayed(const Duration(milliseconds: 400));
    final jsonMap = jsonDecode(_mockRoutesJson) as Map<String, dynamic>;
    return RouteResponse.fromJson(jsonMap);
  }
}

const String _mockRoutesJson = r'''
{
  "success": true,
  "message": "Successfully generated 5 routes",
  "total_count": 5,
  "routes": [
    {
      "id": "route_1",
      "name": "Via Sky Garden at CapitaSpring, Merlion +1 more",
      "distance": 8022,
      "duration": "6821s",
      "score": 0.8,
      "waypoints": [
        {
          "place_id": "ChIJlU3yPoUZ2jERY0LQdNA4KPo",
          "name": "Sky Garden at CapitaSpring",
          "category": "park",
          "search_category": "nature",
          "location": {
            "lat": 1.2838604999999998,
            "lng": 103.8500779,
            "name": "Sky Garden at CapitaSpring"
          },
          "rating": 4.4,
          "distance_km": 1.18
        },
        {
          "place_id": "ChIJ29omWQgZ2jEROEz2yZFzQp8",
          "name": "Merlion",
          "category": "park",
          "search_category": "park",
          "location": {
            "lat": 1.2867891999999999,
            "lng": 103.85450139999999,
            "name": "Merlion"
          },
          "rating": 4.7,
          "distance_km": 0.79
        },
        {
          "place_id": "ChIJUc0YwKIZ2jERnCfsCKnOamE",
          "name": "Fort Canning Tree Tunnel",
          "category": "park",
          "search_category": "park",
          "location": {
            "lat": 1.2972839999999999,
            "lng": 103.846345,
            "name": "Fort Canning Tree Tunnel"
          },
          "rating": 4.3,
          "distance_km": 2.22
        }
      ],
      "geometry": {
        "overview_polyline": {
          "points": "ssyFog|xRtBdAD?n@TVLG`@DNTH[d@BBBGVN?ChFzCZZT?tHdE|@f@g@|@RJS?_BpCI`@_CjEqBhDm@nAOGyB|D[TaAtBBB_@j@JFADb@TWf@m@n@EDXPYVIGBHAb@BJCfBAHYRB?Se@GBHu@BmBKAADq@t@_@F{AC?JFb@CJCh@YLC?Y?QGu@CQDm@AcAESEPaD@WR?A_@Qk@Ge@q@eB?IGEUCReAWCAKBcAqBm@m@MH_AB@BGu@Mk@GAEUEIu@?IPAk@@RfAOX]f@pAL}AbA}ArBFF]`@DDULe@Hs@DGPUXSJG`@q@fA]@QVSZEPYXW`@e@j@IRqAbBDBW`@e@W}BbDEV]OM\DHA@A?OZRJa@z@MBBFIDDFEH@NI?OXITKAEDO?[DSHGBBHGDMZi@Qe@GY?}Cb@k@RKHwC`AOb@QZSFqARw@F{Al@w@ROEKBm@[MJO?eBOID?F@IFCXBA?P@Jw@n@uBVc@d@_@\\QD?@@FCEg@R]\\YXMFKh@Ix@@x@JjANR?pBWP[hAg@d@GFARC|@k@@CAKJOZ{@HQEA\\y@HBABXFBG`@TdFrBDW~BeDDBRa@@@A@XPrAgBHSd@k@Ze@X[@KXe@JM\\Ap@gAFKF_@JATYFQRA?GbAMHCd@i@GG~AuBNGATLHFARMNQl@a@NQh@JH_AB@BGbEfAl@PpBN@f@JHnAVN?JIBKFMLIREzANhBH~BdAZUxB}DdAgB?KjDeGwJyF_@QbAkBNFn@BxAgCIEb@s@Q@c@_@iF{C?Bk@[P]EQFa@WM{@YoBaA"
        },
        "viewport": {
          "low": {
            "latitude": 1.2789180999999998,
            "longitude": 103.84623889999999
          },
          "high": {
            "latitude": 1.2973225,
            "longitude": 103.8605552
          }
        }
      },
      "metadata": {
        "center": [1.2834, 103.8607],
        "search_radius_km": 2.5,
        "route_type": "loop",
        "categories_used": ["nature", "park"]
      }
    },
    {
      "id": "route_2",
      "name": "Via Cloud Forest, Maxwell Food Centre +1 more",
      "distance": 8262,
      "duration": "6864s",
      "score": 0.8,
      "waypoints": [
        {
          "place_id": "ChIJd0VihwEZ2jERKeREhO6G1Qg",
          "name": "Cloud Forest",
          "category": "park",
          "search_category": "nature",
          "location": {
            "lat": 1.2838676999999998,
            "lng": 103.8660024,
            "name": "Cloud Forest"
          },
          "rating": 4.8,
          "distance_km": 0.59
        },
        {
          "place_id": "ChIJseQsTQ0Z2jERqpBTWF0Zf84",
          "name": "Maxwell Food Centre",
          "category": "restaurant",
          "search_category": "restaurant",
          "location": {
            "lat": 1.2803361,
            "lng": 103.844767,
            "name": "Maxwell Food Centre"
          },
          "rating": 4.4,
          "distance_km": 1.8
        },
        {
          "place_id": "ChIJw51YdBIZ2jERoa5GzNLFYvk",
          "name": "JUMBO Seafood - The Riverwalk",
          "category": "restaurant",
          "search_category": "restaurant",
          "location": {
            "lat": 1.2893135,
            "lng": 103.84829479999999,
            "name": "JUMBO Seafood - The Riverwalk"
          },
          "rating": 4.7,
          "distance_km": 1.53
        }
      ],
      "geometry": {
        "overview_polyline": {
          "points": "ssyFog|xRtBdAD?n@TTL^q@FCVCMOe@a@GMSSa@K_@OYI_@@a@IYEGAMGgAQcAK}COuAIY@_B?HoA@SLUf@iCReBLc@x@oAfAOd@KfAa@|AkBL_@BEVAX@RKLMNi@O{@xAY|@LfAWn@KN??Ep@EpBOLC@Bj@ITSDRFXR`@Xv@Rd@~@tAx@~@vBxAlHbEINHDHMjHxD@A`@TRP|BrAjCxADGb@T}BpEeBnCOZa@RqBtDGd@S^_@Z@@MRJDgCjECCMTGCINFDKTQTyBxDWj@QLBBKNAAqA|BuAdC@?OZq@jA_@TMRJFGLMICFEd@}@|Aq@x@s@t@IB[QEBGCYl@\\Ni@lAU`@Qj@DBcAvB@@uBfEA?INo@nAGRsAvCGDJ^VTd@`BNn@NRbDrBHBGZ[n@bAd@HFPRb@TXJ`@Xk@_@OEc@USWkAi@EEABaFaC?CGCA@_Ag@aAg@YQ@AqAo@K?aD_BOQy@e@ABi@Y?AkCsAy@[?BmHmDJCYKEDa@UOXmAxAQXKHPO`@o@v@}@NY`@TXMv@GjBAv@MdAYhDiBVAN@FAl@mARJBBfDn@FDl@NHETWdBcAfBy@Rd@C?ZS@uA@[CKBs@EDHFXWYQRS^a@Vg@c@U@EKG^k@CC`AuBZUxB}DdAgB?KjDeGwJyF_@QbAkBNFn@BxAgCIEb@s@Q@c@_@iF{C?Bk@[P]EQFa@WM{@YoBaA"
        },
        "viewport": {
          "low": {
            "latitude": 1.2741343,
            "longitude": 103.8444117
          },
          "high": {
            "latitude": 1.2889097,
            "longitude": 103.86591759999999
          }
        }
      },
      "metadata": {
        "center": [1.2834, 103.8607],
        "search_radius_km": 2.5,
        "route_type": "loop",
        "categories_used": ["nature", "restaurant"]
      }
    },
    {
      "id": "route_3",
      "name": "Via Floral Fantasy & Jubilee Park",
      "distance": 8150,
      "duration": "6868s",
      "score": 0.8,
      "waypoints": [
        {
          "place_id": "ChIJbf7nMwAZ2jERWNS0iCBvkOQ",
          "name": "Floral Fantasy",
          "category": "park",
          "search_category": "nature",
          "location": {
            "lat": 1.2817383999999998,
            "lng": 103.8611877,
            "name": "Floral Fantasy"
          },
          "rating": 4.5,
          "distance_km": 0.19
        },
        {
          "place_id": "ChIJPV8Z1JwZ2jERKuFD4uIVgOM",
          "name": "Jubilee Park",
          "category": "park",
          "search_category": "park",
          "location": {
            "lat": 1.2937577,
            "lng": 103.8449279,
            "name": "Jubilee Park"
          },
          "rating": 4.7,
          "distance_km": 2.1
        }
      ],
      "geometry": {
        "overview_polyline": {
          "points": "ssyFog|xRtBdAD?n@TTL^q@FCVCMOe@a@GMSSa@K_@OYI_@@a@IYEGAMGgAQcAK}COuAIY@_B?HoA?OvD?\\Ch@BL]lBN\\UNKFIv@Y~@CbBJFVJFCTIVBPNLNBf@l@VTb@L\\ADAf@Wb@Mb@Cd@LTLNNLCBIpAn@FU|JhF`@q@PD^Bh@KF?z@f@Ne@TOVERFMNeEvHEC_@r@HDcClEMEg@|@RJS?_BpCI`@_CjEqBhDm@nAOGyB|D[T_CeAiBI{AOSDMHGLENIDO?sA[GEAg@yBQmCu@{Aa@u@MgQiB[GSIgDm@m@[SGMI_@J_@n@_@p@IJWAQHGH^r@ELw@Y_@S{A~A]j@DFSPCG_@v@GZSb@mAvBSb@MHJFQXEAe@v@QRm@dAA?y@bBDB[v@GCmAdCMJ]UcAb@}@Xe@Hi@BKBHJMHEAm@ZAFgAt@KNJOfAu@@Gp@[D?HGIK\\EVAh@KpAc@j@W\\TLKlAeCFBZw@ECx@cB@?l@eAPSd@w@D@PYKGLI\\u@bAeBRc@F[^w@BFRQEG`@q@vAyAt@\\`@NDM_@s@LMLET@R_@Ze@Xg@^KGe@CIzByCn@s@b@i@HQPu@Fo@HyC?WDIHgCAi@DgCF{DRMGKMHBUF?@m@D?Ia@bABZIRSJWDYX?Db@\\rACpAm@nAA_@tAe@fAQfAAfA@b@FfAZbAb@RHJy@GSTs@ZyAxB?@ArCPlBJdBP^JFDZBTF\\@\\Bd@PPHTDRRFLp@l@@BWBGB_@p@UM{@YoBaA"
        },
        "viewport": {
          "low": {
            "latitude": 1.2769913,
            "longitude": 103.84486489999999
          },
          "high": {
            "latitude": 1.2937325,
            "longitude": 103.8622379
          }
        }
      },
      "metadata": {
        "center": [1.2834, 103.8607],
        "search_radius_km": 2.5,
        "route_type": "loop",
        "categories_used": ["nature", "park"]
      }
    },
    {
      "id": "route_4",
      "name": "Via Golden Mile Food Centre & Bay East Garden",
      "distance": 9770,
      "duration": "8143s",
      "score": 0.8,
      "waypoints": [
        {
          "place_id": "ChIJ04DTdbQZ2jERFt4kBQi-E60",
          "name": "Golden Mile Food Centre",
          "category": "restaurant",
          "search_category": "restaurant",
          "location": {
            "lat": 1.3030907999999999,
            "lng": 103.86392990000002,
            "name": "Golden Mile Food Centre"
          },
          "rating": 4.3,
          "distance_km": 2.22
        },
        {
          "place_id": "ChIJnV5WzKwZ2jERJ8cM9ja9u_M",
          "name": "Bay East Garden",
          "category": "park",
          "search_category": "nature",
          "location": {
            "lat": 1.2881607,
            "lng": 103.869858,
            "name": "Bay East Garden"
          },
          "rating": 4.6,
          "distance_km": 1.15
        }
      ],
      "geometry": {
        "overview_polyline": {
          "points": "ssyFog|xRtBdAD?n@TTL^q@FCVCMOe@a@GMSSa@K_@OYI_@@a@IYEGAMGgAQcAK}COuAIAGoMIiZd@@@P?Aj@S?[Nq@@WIw@AuAFg@Fo@XMFUZTBmCpFGHQKMA[BOFOASNKTCd@[JEFALw@NqBkAIQUCOBGJs@QGl@Dj@o@eAeAqAiDqBa@i@[k@OUw@aBc@i@S[_AeAIWw@kA?QIYsB{CaBr@mDhBGIEBR\\@?Sc@MOaB}Ca@q@G]S]]i@e@Td@U\\h@R\\F\\`@p@`B|CLNRb@OSCKDADH`EsBzDcBFBb@r@DCv@f@v@XPFZ@n@Lz@Hb@H\\Bb@PbBLJPf@b@t@f@JKz@x@TB~AbAJPVH~@Ol@Qt@]ZUt@}@P[Z_ANw@Bm@I{Ba@uFs@kG@e@]kCWmCQmAaA}IIAAJbA|I|@KZGR?PV`@JT?VPn@LTJTFd@RPHPPDCF?BKH?NH`@K^E`AOzBs@hA[\\Ed@?bAFl@?dCIDD@HRGLAjBu@`D{ArEeCtBoAzB{ARG|D{CRSDCfC_CX[LUtAuAh@aA\\Wv@YrAgAvIlMb@jAJb@]?w@LaB|@i@d@eAlAeApAsDhF{AlC]t@Op@APK b@S^eAjAMXKh@@p@]n@e@\\UVa@r@Sx@Cx@D`ACXQ`@y@nAS|@MjAg@hCOZAp@Gj@xB?@ArCPlBJdBP^JFDZBTF\\@\\Bd@PPHTDRRFLp@l@@BWBGB_@p@UM{@YoBaA"
        },
        "viewport": {
          "low": {
            "latitude": 1.2803023,
            "longitude": 103.85869389999999
          },
          "high": {
            "latitude": 1.3030681,
            "longitude": 103.8737302
          }
        }
      },
      "metadata": {
        "center": [1.2834, 103.8607],
        "search_radius_km": 2.5,
        "route_type": "loop",
        "categories_used": ["restaurant", "nature"]
      }
    },
    {
      "id": "route_5",
      "name": "Via Flower Dome, Serene Garden +1 more",
      "distance": 8744,
      "duration": "7330s",
      "score": 0.8,
      "waypoints": [
        {
          "place_id": "ChIJPYrvewEZ2jERK-pztVWcDig",
          "name": "Flower Dome",
          "category": "park",
          "search_category": "nature",
          "location": {
            "lat": 1.2846292,
            "lng": 103.86469749999999,
            "name": "Flower Dome"
          },
          "rating": 4.7,
          "distance_km": 0.46
        },
        {
          "place_id": "ChIJX9eeAB0Z2jER-jpnq5mQijQ",
          "name": "Serene Garden",
          "category": "park",
          "search_category": "park",
          "location": {
            "lat": 1.2784313,
            "lng": 103.8608519,
            "name": "Serene Garden"
          },
          "rating": 4.7,
          "distance_km": 0.55
        },
        {
          "place_id": "ChIJD1u-EaMZ2jERaLhNfFkR45I",
          "name": "National Museum of Singapore",
          "category": "attraction",
          "search_category": "attraction",
          "location": {
            "lat": 1.296613,
            "lng": 103.84850910000002,
            "name": "National Museum of Singapore"
          },
          "rating": 4.6,
          "distance_km": 2.0
        }
      ],
      "geometry": {
        "overview_polyline": {
          "points": "ssyFog|xRtBdAD?n@TTL^q@FCVCMOe@a@GMSSa@K_@OYI_@@a@IYEGAMGgAQcAK}COuAIY@_B?HoA@SLUf@iCReBLc@x@oAfAOd@KfAa@pA}AKo@@SDEW]ISNZVXb@Nh@@DHPh@?VFRPTNh@@\\AXFPJHRFL@`@PVVTf@L\\lCQ^FZNtCjBVnBZH^B`@NrAx@CLHPJHxAPNFr@vALBd@DPFh@r@LB^Bh@KF?z@f@Ne@TOVERFMNeEvHEC_@r@HDcClEMEg@|@RJS?_BpCI`@_CjEqBhDm@nAOGyB|D[T_CeAiBI{AOSDMHGLENIDO?sA[GEAg@yBQmCu@{Aa@u@MgQiB[GSIgDm@m@[SGMI_@J_@n@_@p@IJWAQHGH^r@ELw@Y_@S{A~A]j@DFSPCG_@v@GZSb@mAvBSb@MHJFQXEAe@v@QRm@dAA?y@bBDB[v@GCmAdCMJ]UcAb@}@Xe@Hi@BKBHJMHEAm@ZAFgAt@KNJOfAu@@Gp@[D?HGIK\\EVAh@KpAc@j@W\\TLKlAeCFBZw@ECx@cB@?l@eAPSd@w@D@PYKGLI\\u@bAeBRc@F[^w@BFRQEG`@q@vAyAt@\\`@NDM_@s@LMLET@R_@Ze@Xg@^KGe@CIzByCn@s@b@i@HQPu@Fo@HyC?WDIHgCAi@DgCF{DRMGKMHBUF?@m@D?Ia@bABZIRSJWDYX?Db@\\rACpAm@nAA_@tAe@fAQfAAfA@b@FfAZbAb@RHJy@GSTs@ZyAxB?@ArCPlBJdBP^JFDZBTF\\@\\Bd@PPHTDRRFLp@l@@BWBGB_@p@UM{@YoBaA"
        },
        "viewport": {
          "low": {
            "latitude": 1.2769913,
            "longitude": 103.8487636
          },
          "high": {
            "latitude": 1.2969416,
            "longitude": 103.8651082
          }
        }
      },
      "metadata": {
        "center": [1.2834, 103.8607],
        "search_radius_km": 2.5,
        "route_type": "loop",
        "categories_used": ["attraction", "nature", "park"]
      }
    }
  ]
}
''';
