import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';

import '../../data/models/route.dart';
import '../../providers/location_provider.dart';
import '../../state/routes_controller.dart';
import '../../state/routes_history_controller.dart';
import '../../utils/route_utils.dart';

class MyTrailMapScreen extends ConsumerStatefulWidget {
  const MyTrailMapScreen({super.key});

  @override
  ConsumerState<MyTrailMapScreen> createState() => _MyTrailMapScreenState();
}

class _MyTrailMapScreenState extends ConsumerState<MyTrailMapScreen>
    with TickerProviderStateMixin {
  GoogleMapController? _mapController;
  final TextEditingController _queryController = TextEditingController();
  final DraggableScrollableController _sheetController =
      DraggableScrollableController();

  Waypoint? _focusedWaypoint;
  bool _initialLoadTriggered = false;
  late final AnimationController _rainbowController;

  @override
  void initState() {
    super.initState();
    _rainbowController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )
      ..repeat();

    // Listen to routes controller updates once; avoid re-registering in build.
    ref.listen<RoutesController>(routesControllerProvider, _handleRoutesUpdate);
  }

  @override
  void dispose() {
    _rainbowController.dispose();
    _mapController?.dispose();
    _queryController.dispose();
    super.dispose();
  }

  void _handleRoutesUpdate(RoutesController? previous, RoutesController next) {
    if (mounted && next.error != null && next.error != previous?.error) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text(next.error!),
            action: SnackBarAction(
              label: 'Retry',
              onPressed: () {
                final center = next.center;
                if (center != null) {
                  unawaited(
                    ref
                        .read(routesControllerProvider)
                        .loadRoutes(
                          query: _queryController.text,
                          center: center,
                        ),
                  );
                }
              },
            ),
          ),
        );
    }

    final selectedChanged = previous?.selected?.id != next.selected?.id;
    if (selectedChanged && next.selected != null) {
      unawaited(_animateToRoute(next.selected!));
    }

    final startErrorChanged = previous?.startError != next.startError;
    if (mounted &&
        startErrorChanged &&
        (next.startError ?? '').isNotEmpty) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text(next.startError!),
          ),
        );
    }

    final activeRouteChanged =
        previous?.activeRoute?.id != next.activeRoute?.id;
    if (mounted && activeRouteChanged && next.activeRoute != null) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text('Started route: ${next.activeRoute!.name}'),
          ),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final routesController = ref.watch(routesControllerProvider);
    final locationAsync = ref.watch(currentLocationProvider);
    final historyController = ref.watch(routeHistoryControllerProvider);

    return Scaffold(
      floatingActionButton: locationAsync.maybeWhen<Widget?>(
        data: (_) => Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).padding.bottom + 22,
          ),
          child: FloatingActionButton.extended(
            heroTag: 'history_fab',
            onPressed: _openHistory,
            icon: const Icon(Icons.history),
            label: Text(
              historyController.sessions.isEmpty
                  ? 'History'
                  : 'History (${historyController.sessions.length})',
            ),
          ),
        ),
        orElse: () => null,
      ),
      body: locationAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _LocationErrorView(
          message: error.toString(),
          onRetry: () => ref.refresh(currentLocationProvider),
        ),
        data: (userLocation) {
          // Trigger automatic load on first successful location acquisition.
          if (!_initialLoadTriggered &&
              !routesController.loading &&
              routesController.routes.isEmpty) {
            _initialLoadTriggered = true;
            final initialQuery = _queryController.text.trim();
            if (initialQuery.isNotEmpty) {
              unawaited(
                ref
                    .read(routesControllerProvider)
                    .loadRoutes(
                      query: initialQuery,
                      center: userLocation,
                    ),
              );
            }
          }

          final mapMarkers = _buildMarkers(routesController, userLocation);
          final polylines = _buildPolylines(routesController);
          final circles = _buildCircles(routesController);

          return Stack(
            children: [
              GoogleMap(
                initialCameraPosition: CameraPosition(
                  target: userLocation,
                  zoom: 14,
                ),
                myLocationEnabled: true,
                myLocationButtonEnabled: true,
                compassEnabled: true,
                tiltGesturesEnabled: false,
                mapToolbarEnabled: false,
                rotateGesturesEnabled: false,
                zoomGesturesEnabled: true,
                zoomControlsEnabled: false,
                scrollGesturesEnabled: true,
                polylines: polylines,
                markers: mapMarkers,
                circles: circles,
                onMapCreated: (controller) {
                  _mapController = controller;
                  _maybeFitAllRoutes(routesController);
                },
                onTap: (_) {
                  setState(() => _focusedWaypoint = null);
                },
              ),
              Positioned(
                top: MediaQuery.of(context).padding.top + 16,
                left: 16,
                right: 16,
                child: _SearchBar(
                  controller: _queryController,
                  loading: routesController.loading,
                  animation: _rainbowController,
                  onSubmitted: (value) =>
                      _performSearch(value, routesController, userLocation),
                  onClear: () {
                    _queryController.clear();
                    routesController.clear();
                  },
                ),
              ),
              if (routesController.routes.isNotEmpty)
                Positioned(
                  top: MediaQuery.of(context).padding.top + 76,
                  left: 12,
                  right: 12,
                  child: _LegendRow(
                    routes: routesController.routes,
                    controller: routesController,
                  ),
                ),
              if (routesController.loading)
                const Positioned(top: 16, right: 16, child: _LoadingBadge()),
              Align(
                alignment: Alignment.bottomCenter,
                child: _RouteBottomSheet(
                  controller: routesController,
                  sheetController: _sheetController,
                  onSelect: routesController.selectRoute,
                  onLongPress: _showRouteDetails,
                ),
              ),
              if (_focusedWaypoint != null)
                _WaypointOverlay(
                  waypoint: _focusedWaypoint!,
                  onClose: () => setState(() => _focusedWaypoint = null),
                ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _performSearch(
    String value,
    RoutesController controller,
    LatLng userLocation,
  ) async {
    if (value.trim().isEmpty) {
      return;
    }
    await controller.loadRoutes(query: value.trim(), center: userLocation);
  }

  Set<Marker> _buildMarkers(RoutesController controller, LatLng userLocation) {
    final markers = <Marker>{
      Marker(
        markerId: const MarkerId('user_center'),
        position: userLocation,
        infoWindow: const InfoWindow(title: 'You are here'),
        icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueAzure),
      ),
    };

    final selected = controller.selected;
    final waypoints = controller.allWaypoints();

    for (final waypoint in waypoints) {
      if (!controller.isCategoryVisible(waypoint.category)) {
        continue;
      }
      markers.add(
        Marker(
          markerId: MarkerId(waypoint.placeId),
          position: LatLng(waypoint.location.lat, waypoint.location.lng),
          infoWindow: InfoWindow(
            title: waypoint.name,
            snippet: _buildWaypointSnippet(waypoint),
          ),
          icon: BitmapDescriptor.defaultMarkerWithHue(
            categoryHue(waypoint.category),
          ),
          onTap: () => setState(() => _focusedWaypoint = waypoint),
        ),
      );
    }

    if (selected != null && selected.waypoints.length >= 2) {
      final first = selected.waypoints.first;
      final last = selected.waypoints.last;
      markers
        ..add(
          Marker(
            markerId: MarkerId('${selected.id}_start'),
            position: LatLng(first.location.lat, first.location.lng),
            infoWindow: const InfoWindow(title: 'Start'),
            icon: BitmapDescriptor.defaultMarkerWithHue(
              BitmapDescriptor.hueGreen,
            ),
          ),
        )
        ..add(
          Marker(
            markerId: MarkerId('${selected.id}_end'),
            position: LatLng(last.location.lat, last.location.lng),
            infoWindow: const InfoWindow(title: 'End'),
            icon: BitmapDescriptor.defaultMarkerWithHue(
              BitmapDescriptor.hueRed,
            ),
          ),
        );
    }

    return markers;
  }

  Set<Polyline> _buildPolylines(RoutesController controller) {
    if (controller.routes.isEmpty) {
      return const <Polyline>{};
    }

    final selected = controller.selected;
    final polylines = <Polyline>{};

    for (final route in controller.routes) {
      final encoded = route.geometry.overviewPolyline.points;
      if (encoded.isEmpty) {
        continue;
      }

      final points = decodePolyline(encoded);
      if (points.length < 2) {
        continue;
      }

      final isSelected = identical(route, selected) || route.id == selected?.id;
      final category = _primaryCategory(route) ?? 'default';
      final color = isSelected
          ? categoryColor(category)
          : Colors.grey.shade500;

      polylines.add(
        Polyline(
          polylineId: PolylineId(route.id),
          points: points,
          color: color,
          width: isSelected ? 6 : 2,
          zIndex: isSelected ? 2 : 1,
        ),
      );
    }

    return polylines;
  }

  Set<Circle> _buildCircles(RoutesController controller) {
    final selected = controller.selected;
    if (selected == null) {
      return const {};
    }

    final metadata = selected.metadata;
    if (metadata.center.length < 2 || metadata.searchRadiusKm == null) {
      return const {};
    }

    final centerLat = metadata.center[0];
    final centerLng = metadata.center[1];
    final category = _primaryCategory(selected) ?? 'default';
    final color = categoryColor(category);

    return {
      Circle(
        circleId: CircleId('radius_${selected.id}'),
        center: LatLng(centerLat, centerLng),
        radius: metadata.searchRadiusKm! * 1000,
        strokeColor: color.withOpacity(0.6),
        strokeWidth: 1,
        fillColor: color.withOpacity(0.03),
      ),
    };
  }

  String _buildWaypointSnippet(Waypoint waypoint) {
    final parts = <String>[waypoint.category];
    if (waypoint.rating != null) {
      parts.add('★ ${waypoint.rating!.toStringAsFixed(1)}');
    }
    if (waypoint.distanceKm != null) {
      parts.add('${_distanceLabel(waypoint.distanceKm!)} away');
    }
    return parts.join(' • ');
  }

  String _distanceLabel(double distanceKm) {
    if (distanceKm < 1) {
      return '${(distanceKm * 1000).round()} m';
    }
    return '${distanceKm.toStringAsFixed(1)} km';
  }

  String? _primaryCategory(MtRoute route) {
    if (route.metadata.categoriesUsed != null &&
        route.metadata.categoriesUsed!.isNotEmpty) {
      return route.metadata.categoriesUsed!.first;
    }
    if (route.waypoints.isNotEmpty) {
      return route.waypoints.first.category;
    }
    return null;
  }

  Future<void> _animateToRoute(MtRoute route) async {
    final controller = _mapController;
    if (controller == null) {
      return;
    }

    final bounds = boundsFromViewport(route.geometry.viewport);
    try {
      await controller.animateCamera(CameraUpdate.newLatLngBounds(bounds, 48));
    } catch (_) {
      await Future<void>.delayed(const Duration(milliseconds: 300));
      unawaited(
        controller.animateCamera(CameraUpdate.newLatLngBounds(bounds, 48)),
      );
    }
  }

  void _maybeFitAllRoutes(RoutesController controller) {
    if (controller.routes.isEmpty) {
      return;
    }

    final bounds = _combineBounds(controller.routes);
    if (bounds == null) {
      return;
    }

    final mapController = _mapController;
    if (mapController == null) {
      return;
    }

    unawaited(
      mapController.animateCamera(CameraUpdate.newLatLngBounds(bounds, 64)),
    );
  }

  LatLngBounds? _combineBounds(List<MtRoute> routes) {
    if (routes.isEmpty) {
      return null;
    }

    double south = double.infinity;
    double north = -double.infinity;
    double west = double.infinity;
    double east = -double.infinity;

    for (final route in routes) {
      final viewport = route.geometry.viewport;
      final low = viewport.low;
      final high = viewport.high;
      south = math.min(south, math.min(low.lat, high.lat));
      north = math.max(north, math.max(low.lat, high.lat));
      west = math.min(west, math.min(low.lng, high.lng));
      east = math.max(east, math.max(low.lng, high.lng));
    }

    if (south == double.infinity) {
      return null;
    }

    return LatLngBounds(
      southwest: LatLng(south, west),
      northeast: LatLng(north, east),
    );
  }

  void _openHistory() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (modalContext) {
        return FractionallySizedBox(
          heightFactor: 0.75,
          child: _RouteHistorySheet(
            onSelect: (session, route) {
              Navigator.of(modalContext).pop();
              ref
                  .read(routesControllerProvider)
                  .displayHistorySession(
                    session,
                    routeId: route.id,
                  );
              setState(() => _focusedWaypoint = null);
            },
          ),
        );
      },
    );
  }

  void _showRouteDetails(MtRoute route) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        final theme = Theme.of(context);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        route.name,
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text('Distance: ${formatDistance(route.distance)}'),
                Text('Duration: ${formatDuration(route.duration)}'),
                Text('Score: ${(route.score * 100).toStringAsFixed(0)}% match'),
                if (route.metadata.categoriesUsed != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final category in route.metadata.categoriesUsed!)
                          Chip(
                            backgroundColor: categoryColor(
                              category,
                            ).withOpacity(0.15),
                            label: Text(category),
                          ),
                      ],
                    ),
                  ),
                const SizedBox(height: 16),
                Text('Waypoints', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                ...route.waypoints.map(
                  (wp) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      categoryIcon(wp.category),
                      color: categoryColor(wp.category),
                    ),
                    title: Text(wp.name),
                    subtitle: Text(_buildWaypointSnippet(wp)),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _RouteHistorySheet extends ConsumerWidget {
  const _RouteHistorySheet({required this.onSelect});

  final void Function(RouteHistorySession session, RouteHistoryRoute route)
      onSelect;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final historyController = ref.watch(routeHistoryControllerProvider);
    final sessions = historyController.sessions;
    final theme = Theme.of(context);

    return Material(
      color: theme.colorScheme.surface,
      borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      child: Column(
        children: [
          const SizedBox(height: 12),
          const _HistorySheetHandle(),
          const SizedBox(height: 12),
          Text('Search History', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Expanded(
            child: sessions.isEmpty
                ? const _EmptyHistoryView()
                : ListView.separated(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 12,
                    ),
                    itemCount: sessions.length,
                    itemBuilder: (context, index) {
                      final session = sessions[index];
                      return _HistorySessionTile(
                        session: session,
                        onSelect: (route) => onSelect(session, route),
                      );
                    },
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                  ),
          ),
        ],
      ),
    );
  }
}

class _HistorySessionTile extends StatelessWidget {
  const _HistorySessionTile({
    required this.session,
    required this.onSelect,
  });

  final RouteHistorySession session;
  final ValueChanged<RouteHistoryRoute> onSelect;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    _formatHistoryTimestamp(session.timestamp),
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                Text(
                  '${session.routes.length} routes',
                  style: theme.textTheme.labelMedium,
                ),
              ],
            ),
            if ((session.query ?? '').isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  'Query: ${session.query}',
                  style: theme.textTheme.bodySmall,
                ),
              ),
            if (session.totalCount != null &&
                session.totalCount! > session.routes.length)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  '${session.totalCount} total suggestions',
                  style: theme.textTheme.labelSmall,
                ),
              ),
            const SizedBox(height: 12),
            for (var i = 0; i < session.routes.length; i++) ...[
              _HistoryRouteTile(
                route: session.routes[i],
                onTap: () => onSelect(session.routes[i]),
              ),
              if (i != session.routes.length - 1)
                Divider(color: Colors.grey.shade200, height: 16),
            ],
          ],
        ),
      ),
    );
  }
}

class _HistoryRouteTile extends StatelessWidget {
  const _HistoryRouteTile({
    required this.route,
    required this.onTap,
  });

  final RouteHistoryRoute route;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mtRoute = route.toMtRoute();
    final details = <String>[
      formatDistance(mtRoute.distance),
      formatDuration(mtRoute.duration),
    ];
    if (mtRoute.score > 0) {
      details.add('${(mtRoute.score * 100).round()}% match');
    }
    final primaryCategory = mtRoute.metadata.categoriesUsed?.first ??
        (mtRoute.waypoints.isNotEmpty ? mtRoute.waypoints.first.category : null);

    final categoryColorValue = primaryCategory == null
        ? Colors.grey.shade200
        : categoryColor(primaryCategory).withOpacity(0.2);
    final categoryIconValue = primaryCategory == null
        ? Icons.route
        : categoryIcon(primaryCategory);
    final categoryForeground = primaryCategory == null
        ? Colors.grey.shade700
        : categoryColor(primaryCategory);

    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: CircleAvatar(
        backgroundColor: categoryColorValue,
        child: Icon(
          categoryIconValue,
          color: categoryForeground,
        ),
      ),
      title: Text(
        mtRoute.name.isEmpty ? 'Route ${mtRoute.id}' : mtRoute.name,
        style: theme.textTheme.titleMedium,
      ),
      subtitle: Text(details.join(' • ')),
      trailing: const Icon(Icons.chevron_right),
      onTap: onTap,
    );
  }
}

class _HistorySheetHandle extends StatelessWidget {
  const _HistorySheetHandle();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      height: 4,
      decoration: BoxDecoration(
        color: Colors.grey.shade400,
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }
}

class _EmptyHistoryView extends StatelessWidget {
  const _EmptyHistoryView();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.history, size: 48, color: theme.colorScheme.outline),
          const SizedBox(height: 12),
          Text('No searches yet', style: theme.textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            'Run a search to start building your history.',
            style: theme.textTheme.bodyMedium,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

String _formatHistoryTimestamp(DateTime timestamp) {
  final local = timestamp.toLocal();
  String twoDigits(int value) => value.toString().padLeft(2, '0');
  return '${local.year.toString().padLeft(4, '0')}-'
      '${twoDigits(local.month)}-'
      '${twoDigits(local.day)} '
      '${twoDigits(local.hour)}:${twoDigits(local.minute)}';
}

class _SearchBar extends StatelessWidget {
  const _SearchBar({
    required this.controller,
    required this.loading,
    required this.animation,
    required this.onSubmitted,
    required this.onClear,
  });

  final TextEditingController controller;
  final bool loading;
  final Animation<double> animation;
  final ValueChanged<String> onSubmitted;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return AnimatedBuilder(
      animation: animation,
      builder: (context, child) {
        final gradient = SweepGradient(
          transform: GradientRotation(animation.value * 2 * math.pi),
          colors: const [
            Colors.red,
            Colors.orange,
            Colors.yellow,
            Colors.green,
            Colors.blue,
            Colors.indigo,
            Colors.purple,
            Colors.red,
          ],
        );

        return Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            gradient: gradient,
          ),
          padding: const EdgeInsets.all(3),
          child: Material(
            elevation: 4,
            borderRadius: BorderRadius.circular(12),
            clipBehavior: Clip.antiAlias,
            child: TextField(
              controller: controller,
              textInputAction: TextInputAction.search,
              onSubmitted: onSubmitted,
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search),
                suffixIcon: loading
                    ? const Padding(
                        padding: EdgeInsets.all(12),
                        child: SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      )
                    : IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: onClear,
                      ),
                hintText: 'Let\'s start to explore!',
                filled: true,
                fillColor: theme.colorScheme.surface,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(
                    color: theme.dividerColor.withOpacity(0.3),
                  ),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(
                    color: theme.dividerColor.withOpacity(0.3),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _LegendRow extends StatelessWidget {
  const _LegendRow({required this.routes, required this.controller});

  final List<MtRoute> routes;
  final RoutesController controller;

  @override
  Widget build(BuildContext context) {
    final categories = <String>{};
    for (final route in routes) {
      if (route.metadata.categoriesUsed != null) {
        categories.addAll(route.metadata.categoriesUsed!);
      } else {
        categories.addAll(route.waypoints.map((wp) => wp.category));
      }
    }

    if (categories.isEmpty) {
      return const SizedBox.shrink();
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: Row(
        children: [
          for (final category in categories)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: FilterChip(
                selected: controller.isCategoryVisible(category),
                label: Text(category),
                selectedColor: categoryColor(category).withOpacity(0.2),
                checkmarkColor: categoryColor(category),
                avatar: Icon(
                  categoryIcon(category),
                  size: 18,
                  color: categoryColor(category),
                ),
                onSelected: (_) =>
                    controller.toggleCategoryVisibility(category),
              ),
            ),
        ],
      ),
    );
  }
}

class _RouteBottomSheet extends StatefulWidget {
  const _RouteBottomSheet({
    required this.controller,
    required this.onSelect,
    required this.onLongPress,
    required this.sheetController,
  });

  final RoutesController controller;
  final void Function(MtRoute route) onSelect;
  final void Function(MtRoute route) onLongPress;
  final DraggableScrollableController sheetController;

  @override
  _RouteBottomSheetState createState() => _RouteBottomSheetState();
}

class _RouteBottomSheetState extends State<_RouteBottomSheet> {
  static const double _minSheetSize = 0.15;
  static const double _maxSheetSize = 0.5;

  Future<void> _handleStartRoute(MtRoute route) async {
    final error = await widget.controller.startRoute(route: route);
    if (!mounted) {
      return;
    }
    if (error == null) {
      unawaited(
        widget.sheetController.animateTo(
          _minSheetSize,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeInOut,
        ),
      );
    }
  }

  void _handleReturnToRoutes() {
    widget.controller.resetActiveRoute();
    unawaited(
      widget.sheetController.animateTo(
        _maxSheetSize,
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeInOut,
      ),
    );
  }

  void _toggleSheetSize() {
    final currentSize = widget.sheetController.size;
    if (currentSize > (_minSheetSize + 0.01)) {
      widget.sheetController.animateTo(
        _minSheetSize,
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeInOut,
      );
    } else {
      widget.sheetController.animateTo(
        _maxSheetSize,
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeInOut,
      );
    }
  }

  Widget _buildHandleWidget() {
    return Center(
      child: GestureDetector(
        onTap: _toggleSheetSize,
        child: Container(
          width: 40,
          height: 4,
          decoration: BoxDecoration(
            color: Colors.grey.shade400,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      controller: widget.sheetController,
      initialChildSize: 0.18,
      minChildSize: _minSheetSize,
      maxChildSize: _maxSheetSize,
      builder: (context, scrollController) {
        final controller = widget.controller;
        if (controller.routes.isEmpty) {
          return const SizedBox.shrink();
        }

        if (controller.hasActiveRoute && controller.activeRoute != null) {
          final route = controller.activeRoute!;
          return DecoratedBox(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surface,
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(20)),
              boxShadow: [
                BoxShadow(
                  blurRadius: 12,
                  color: Colors.black.withOpacity(0.15),
                  offset: const Offset(0, -4),
                ),
              ],
            ),
            child: ListView(
              controller: scrollController,
              padding: EdgeInsets.zero,
              physics: const ClampingScrollPhysics(),
              children: [
                const SizedBox(height: 12),
                _buildHandleWidget(),
                const SizedBox(height: 16),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: _ActiveRouteCard(
                    route: route,
                    onReturn: _handleReturnToRoutes,
                  ),
                ),
                const SizedBox(height: 16),
              ],
            ),
          );
        }

        return DecoratedBox(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
            boxShadow: [
              BoxShadow(
                blurRadius: 12,
                color: Colors.black.withOpacity(0.15),
                offset: const Offset(0, -4),
              ),
            ],
          ),
          child: CustomScrollView(
            controller: scrollController,
            slivers: [
              const SliverToBoxAdapter(child: SizedBox(height: 12)),
              SliverToBoxAdapter(child: _buildHandleWidget()),
              const SliverToBoxAdapter(child: SizedBox(height: 12)),
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final route = controller.routes[index];
                    final isSelected = controller.selected?.id == route.id;
                    final showStartButton =
                        isSelected && !controller.hasActiveRoute;
                    return _RouteListTile(
                      route: route,
                      isSelected: isSelected,
                      showStartButton: showStartButton,
                      startInProgress: controller.startingRoute,
                      onStart: showStartButton
                          ? () => _handleStartRoute(route)
                          : null,
                      onTap: () => widget.onSelect(route),
                      onLongPress: () => widget.onLongPress(route),
                    );
                  },
                  childCount: controller.routes.length,
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 12)),
            ],
          ),
        );
      },
    );
  }
}

class _RouteListTile extends StatelessWidget {
  const _RouteListTile({
    required this.route,
    required this.isSelected,
    required this.showStartButton,
    required this.startInProgress,
    this.onStart,
    required this.onTap,
    required this.onLongPress,
  });

  final MtRoute route;
  final bool isSelected;
  final bool showStartButton;
  final bool startInProgress;
  final VoidCallback? onStart;
  final VoidCallback onTap;
  final VoidCallback onLongPress;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = categoryColor(
      route.metadata.categoriesUsed?.first ??
          route.waypoints.firstOrNull?.category ??
          'default',
    );

    return InkWell(
      onTap: onTap,
      onLongPress: onLongPress,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 6,
              height: 64,
              decoration: BoxDecoration(
                color: isSelected ? color : Colors.grey.shade300,
                borderRadius: BorderRadius.circular(3),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          route.name,
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: isSelected
                                ? FontWeight.w600
                                : FontWeight.w500,
                          ),
                        ),
                      ),
                      if (route.metadata.categoriesUsed != null &&
                          route.metadata.categoriesUsed!.isNotEmpty)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.grey.shade200,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            route.metadata.categoriesUsed!.first,
                            style: theme.textTheme.labelSmall,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Text(formatDistance(route.distance)),
                      const SizedBox(width: 12),
                      Text(formatDuration(route.duration)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: LinearProgressIndicator(
                      minHeight: 6,
                      value: route.score.clamp(0.0, 1.0),
                      backgroundColor: Colors.grey.shade200,
                      valueColor: AlwaysStoppedAnimation<Color>(color),
                    ),
                  ),
                  if (showStartButton) ...[
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: FilledButton.icon(
                        onPressed: startInProgress ? null : onStart,
                        icon: startInProgress
                            ? SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.play_arrow),
                        label: Text(
                          startInProgress ? 'Starting...' : 'Start',
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActiveRouteCard extends StatelessWidget {
  const _ActiveRouteCard({required this.route, required this.onReturn});

  final MtRoute route;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final details = <String>[
      formatDistance(route.distance),
      formatDuration(route.duration),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Route started',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest
                .withValues(alpha: 0.6),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                route.name.isEmpty ? 'Route ${route.id}' : route.name,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(details.join(' • ')),
              if (route.metadata.categoriesUsed != null &&
                  route.metadata.categoriesUsed!.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Wrap(
                    spacing: 8,
                    children: [
                      for (final category
                          in route.metadata.categoriesUsed!.take(3))
                        Chip(
                          label: Text(category),
                          backgroundColor: categoryColor(category)
                              .withValues(alpha: 0.15),
                        ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: onReturn,
          icon: const Icon(Icons.arrow_back),
          label: const Text('Back to routes'),
        ),
      ],
    );
  }
}

class _WaypointOverlay extends StatelessWidget {
  const _WaypointOverlay({required this.waypoint, required this.onClose});

  final Waypoint waypoint;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.bottomCenter,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Material(
          borderRadius: BorderRadius.circular(16),
          color: Theme.of(context).colorScheme.surface,
          elevation: 8,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  categoryIcon(waypoint.category),
                  color: categoryColor(waypoint.category),
                ),
                const SizedBox(width: 16),
                Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      waypoint.name,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _buildSnippet(waypoint),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
                IconButton(onPressed: onClose, icon: const Icon(Icons.close)),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _buildSnippet(Waypoint waypoint) {
    final parts = <String>[waypoint.category];
    if (waypoint.rating != null) {
      parts.add('★ ${waypoint.rating!.toStringAsFixed(1)}');
    }
    if (waypoint.distanceKm != null) {
      parts.add('${waypoint.distanceKm!.toStringAsFixed(1)} km away');
    }
    return parts.join(' • ');
  }
}

class _LocationErrorView extends StatelessWidget {
  const _LocationErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.location_off, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              'Location unavailable',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}

class _LoadingBadge extends StatelessWidget {
  const _LoadingBadge();

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      elevation: 4,
      borderRadius: BorderRadius.circular(20),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: const [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(width: 8),
            Text('Loading routes...'),
          ],
        ),
      ),
    );
  }
}

extension on List<Waypoint> {
  Waypoint? get firstOrNull => isEmpty ? null : first;
}
