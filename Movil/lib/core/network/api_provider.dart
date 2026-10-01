import 'package:dio/dio.dart';
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'interceptors/auth_interceptor.dart';

/// Un envoltorio (wrapper) brutalmente abstracto y fácil de usar para las peticiones HTTP.
/// Maneja internamente los interceptores, timeouts y el mapeo de errores.
class ApiProvider {
  static final ApiProvider _instance = ApiProvider._internal();
  late Dio _dio;

  /// Retorna la instancia global (Singleton)
  factory ApiProvider() {
    return _instance;
  }

  ApiProvider._internal() {
    String baseUrl = dotenv.env['API_URL_LOCAL'] ?? 'http://localhost:5080/api';
    if (!kIsWeb && Platform.isAndroid) {
      baseUrl = dotenv.env['API_URL_ANDROID'] ?? 'http://10.0.2.2:5080/api';
    }

    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // Agregamos el interceptor de autenticación
    _dio.interceptors.add(AuthInterceptor());

    // Agregamos un logger solo en modo de desarrollo
    if (kDebugMode) {
      _dio.interceptors.add(LogInterceptor(
        request: true,
        requestHeader: true,
        requestBody: true,
        responseHeader: true,
        responseBody: true,
        error: true,
      ));
    }
  }

  /// Expone la instancia interna de Dio por si se requiere configuración muy específica en algún caso aislado
  Dio get dioClient => _dio;

  /// [GET] - Obtener datos
  Future<dynamic> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      final response = await _dio.get(
        path,
        queryParameters: queryParameters,
        options: options,
        cancelToken: cancelToken,
      );
      return _handleResponse(response);
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// [POST] - Enviar o crear datos
  Future<dynamic> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      final response = await _dio.post(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
        cancelToken: cancelToken,
      );
      return _handleResponse(response);
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// [PUT] - Reemplazar datos completamente
  Future<dynamic> put(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      final response = await _dio.put(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
        cancelToken: cancelToken,
      );
      return _handleResponse(response);
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// [PATCH] - Actualizar datos parcialmente
  Future<dynamic> patch(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      final response = await _dio.patch(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
        cancelToken: cancelToken,
      );
      return _handleResponse(response);
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// [DELETE] - Eliminar datos
  Future<dynamic> delete(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      final response = await _dio.delete(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
        cancelToken: cancelToken,
      );
      return _handleResponse(response);
    } catch (e) {
      throw _handleError(e);
    }
  }

  /// Centraliza la validación de las respuestas exitosas
  dynamic _handleResponse(Response response) {
    if (response.statusCode != null &&
        response.statusCode! >= 200 &&
        response.statusCode! < 300) {
      return response.data; // Puede ser un Map, List o String dependiendo del JSON
    } else {
      throw Exception('Error del servidor: Código ${response.statusCode}');
    }
  }

  /// Transforma los errores crudos de Dio en excepciones claras para la app
  Exception _handleError(dynamic error) {
    if (error is DioException) {
      switch (error.type) {
        case DioExceptionType.connectionTimeout:
        case DioExceptionType.sendTimeout:
        case DioExceptionType.receiveTimeout:
          return Exception('Tiempo de espera agotado. Verifica tu conexión a internet.');
        
        case DioExceptionType.badResponse:
          final statusCode = error.response?.statusCode;
          // Intenta extraer un mensaje de error que venga en el JSON de la API
          final message = error.response?.data?['message'] ?? error.message;
          return Exception('Error $statusCode: $message');
          
        case DioExceptionType.cancel:
          return Exception('La petición fue cancelada.');
          
        case DioExceptionType.connectionError:
          return Exception('No hay conexión a internet o el servidor no es alcanzable.');
          
        default:
          return Exception('Error desconocido: ${error.message}');
      }
    }
    // Si no es un error de Dio (ej. error de parseo en el cliente)
    return Exception('Ocurrió un error inesperado en la aplicación.');
  }
}

/// Instancia global exportada lista para usarse en toda la app.
/// Ejemplo de uso:
/// ```dart
/// final response = await api.get('/usuarios');
/// ```
final api = ApiProvider();
