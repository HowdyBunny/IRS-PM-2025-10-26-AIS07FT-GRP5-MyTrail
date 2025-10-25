import 'dart:async';

import 'package:dio/dio.dart';

import '../data/models/route.dart';

/// Exception thrown when the routes API fails.
class RoutesException implements Exception {
  RoutesException(this.message, {this.cause});

  final String message;
  final Object? cause;

  @override
  String toString() => message;
}

/// API client responsible for fetching routes from the backend.
class RoutesApi {
  RoutesApi(this._dio) {
    final baseUrl = _dio.options.baseUrl;
    if (baseUrl.isEmpty) {
      _dio.options = _dio.options.copyWith(
        baseUrl: const String.fromEnvironment(
          'API_BASE_URL',
          defaultValue: 'http://192.168.0.207:8000', // for iPhone testing
          // defaultValue: 'http://0.0.0.0:8000', // for local testing
        ),
        sendTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 30),
        connectTimeout: const Duration(seconds: 15),
        contentType: Headers.jsonContentType,
        responseType: ResponseType.json,
        headers: const {
          Headers.acceptHeader: Headers.jsonContentType,
        },
      );
    }
  }

  final Dio _dio;

  /// Fetch routes for the given query and center point.
  Future<RouteResponse> fetchRoutes({
    required String query,
    required double lat,
    required double lng,
  }) async {
    try {
      final payload = {
        'query': query,
        'center': {'lat': lat, 'lng': lng},
      };

      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/routes/query',
        data: payload,
        options: Options(
          sendTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 30),
        ),
      );

      final data = response.data;
      if (data == null) {
        throw RoutesException('No response from server. Please try again.');
      }

      return RouteResponse.fromJson(data);
    } on DioException catch (error) {
      throw RoutesException(_mapDioError(error), cause: error);
    } catch (error) {
      throw RoutesException(
        'Unexpected error. Please try again later.',
        cause: error,
      );
    }
  }

  /// Send feedback about which route the user decided to start.
  Future<void> submitFeedback(List<Map<String, dynamic>> payload) async {
    try {
      await _dio.post<void>(
        '/api/v1/feedback',
        data: payload,
        options: Options(
          sendTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        ),
      );
    } on DioException catch (error) {
      throw RoutesException(_mapDioError(error), cause: error);
    } catch (error) {
      throw RoutesException(
        'Unexpected error sending feedback. Please try again later.',
        cause: error,
      );
    }
  }

  String _mapDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'Unable to connect to the server. Please check your connection.';
      case DioExceptionType.badCertificate:
        return 'Secure connection failed. Please try again later.';
      case DioExceptionType.cancel:
        return 'Request cancelled.';
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode ?? 0;
        if (statusCode >= 500) {
          return 'Server error ($statusCode). Please try again later.';
        }
        if (statusCode == 404) {
          return 'Routes service unavailable. Try again soon.';
        }
        if (statusCode == 401 || statusCode == 403) {
          return 'Access denied. Check your credentials.';
        }
        final message = error.response?.data;
        if (message is Map<String, dynamic>) {
          final text =
              message['message'] as String? ?? message['error'] as String?;
          if (text != null && text.isNotEmpty) {
            return text;
          }
        }
        return 'Request failed ($statusCode). Please adjust your filters and retry.';
      case DioExceptionType.connectionError:
      case DioExceptionType.unknown:
        if (error.error is TimeoutException) {
          return 'Unable to connect to the server. Please check your connection.';
        }
        return 'Unable to connect to the server. Please check your connection.';
    }
  }
}
