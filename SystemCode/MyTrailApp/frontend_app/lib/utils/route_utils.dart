import 'dart:math' as math;

import 'package:flutter/material.dart' hide Viewport;
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:intl/intl.dart';
import 'package:google_polyline_algorithm/google_polyline_algorithm.dart'
    as poly;

import '../data/models/route.dart';

/// Cached formatter for distance strings with a single decimal digit.
final _distanceFormat = NumberFormat('0.0');

/// Decode an encoded polyline string into a list of [LatLng] points.
List<LatLng> decodePolyline(String encoded) {
  if (encoded.isEmpty) {
    return const [];
  }

  final decoded = poly.decodePolyline(encoded);
  if (decoded.isEmpty) {
    return const [];
  }

  return decoded
      .map((point) => LatLng(point[0].toDouble(), point[1].toDouble()))
      .toList(growable: false);
}

/// Convert the backend viewport to a [LatLngBounds] for map camera fitting.
LatLngBounds boundsFromViewport(Viewport viewport) {
  final low = viewport.low;
  final high = viewport.high;

  final double south = math.min(low.lat, high.lat).toDouble();
  final double north = math.max(low.lat, high.lat).toDouble();
  final double west = math.min(low.lng, high.lng).toDouble();
  final double east = math.max(low.lng, high.lng).toDouble();

  return LatLngBounds(
    southwest: LatLng(south, west),
    northeast: LatLng(north, east),
  );
}

/// Format a distance from meters to a human friendly string.
String formatDistance(int meters) {
  if (meters < 0) {
    return '0 m';
  }
  if (meters < 1000) {
    return '${meters.round()} m';
  }
  final kilometers = meters / 1000;
  return '${_distanceFormat.format(kilometers)} km';
}

/// Format a duration expressed like "5876s" into `mm:ss` or `xh ym`.
String formatDuration(String secondsLike) {
  final seconds =
      int.tryParse(secondsLike.replaceAll(RegExp('[^0-9]'), '')) ?? 0;
  final duration = Duration(seconds: seconds);

  if (duration.inHours >= 1) {
    final remainingMinutes = duration.inMinutes % 60;
    return '${duration.inHours}h ${remainingMinutes}m';
  }

  final minutes = duration.inMinutes;
  final secs = duration.inSeconds % 60;
  final minutesString = minutes.toString().padLeft(2, '0');
  final secondsString = secs.toString().padLeft(2, '0');
  return '$minutesString:$secondsString';
}

/// Lookup of category name to Google Maps marker hue.
const Map<String, double> _categoryHue = {
  'park': BitmapDescriptor.hueGreen,
  'nature': BitmapDescriptor.hueGreen,
  'restaurant': BitmapDescriptor.hueRed,
  'attraction': BitmapDescriptor.hueAzure,
};

/// Lookup of category name to [Color].
const Map<String, Color> _categoryColor = {
  'park': Colors.green,
  'nature': Colors.green,
  'restaurant': Colors.red,
  'attraction': Colors.blue,
};

/// Lookup of category name to [IconData].
const Map<String, IconData> _categoryIcon = {
  'park': Icons.park,
  'nature': Icons.eco,
  'restaurant': Icons.restaurant,
  'attraction': Icons.place,
};

/// Returns the Google Maps hue for a given waypoint category.
double categoryHue(String category) {
  final key = category.toLowerCase();
  return _categoryHue[key] ?? BitmapDescriptor.hueViolet;
}

/// Returns the UI color for a given category.
Color categoryColor(String category) {
  final key = category.toLowerCase();
  return _categoryColor[key] ?? Colors.deepPurple;
}

/// Returns a suggested icon for the category, defaults to a location pin.
IconData categoryIcon(String category) {
  final key = category.toLowerCase();
  return _categoryIcon[key] ?? Icons.location_on;
}
