import '../models/ruta_trabajo.dart';
import '../../../core/network/api_provider.dart';

class RutasTrabajoService {
  final ApiProvider _api = ApiProvider();

  Future<List<RutaTrabajo>> obtenerRutasAsignadas({
    required String operario,
  }) async {
    if (operario.trim().isEmpty) {
      throw ArgumentError('Se requiere el empleado autenticado.');
    }
    final res = await _api.get(
      '/rutas-trabajo/asignadas',
      queryParameters: {'operario': operario},
    );
    if (res is! List) {
      throw const FormatException('Respuesta de rutas inválida');
    }
    return res
        .map((r) => RutaTrabajo.fromJson(Map<String, dynamic>.from(r as Map)))
        .toList();
  }

  Future<RutaTrabajo> obtenerDetalleRuta(int rutaId) async {
    final res = await _api.get('/rutas-trabajo/$rutaId');
    if (res is! Map<String, dynamic>) {
      throw const FormatException('Detalle de ruta inválido');
    }
    return RutaTrabajo.fromJson(res);
  }

  Future<void> iniciarRuta(int rutaId) async {
    await _api.put('/rutas-trabajo/$rutaId/iniciar');
  }

  Future<ResultadoEjecucionPunto> ejecutarAccionPunto({
    required int rutaId,
    required int puntoId,
    String? observaciones,
    double? latitudMovil,
    double? longitudMovil,
    double? lecturaMedidor,
    String? estadoFinal,
    String? motivoObservacion,
    List<String>? fotos,
  }) async {
    try {
      final Map<String, dynamic> body = {
        'observaciones':
            observaciones ?? 'Operativo ejecutado en campo con éxito.',
      };
      if (latitudMovil != null) body['latitudMovil'] = latitudMovil;
      if (longitudMovil != null) body['longitudMovil'] = longitudMovil;
      if (lecturaMedidor != null) body['lecturaMedidor'] = lecturaMedidor;
      if (estadoFinal != null && estadoFinal.isNotEmpty) {
        body['estadoFinal'] = estadoFinal;
      }
      if (motivoObservacion != null && motivoObservacion.isNotEmpty) {
        body['motivoObservacion'] = motivoObservacion;
      }
      if (fotos != null && fotos.isNotEmpty) body['fotos'] = fotos;

      final res = await _api.put(
        '/rutas-trabajo/$rutaId/puntos/$puntoId/ejecutar',
        data: body,
      );
      return ResultadoEjecucionPunto(exito: res != null);
    } catch (e) {
      final errMsg = e.toString().replaceAll('Exception: ', '');
      final isAntifraude =
          errMsg.toLowerCase().contains('antifraude') ||
          errMsg.toLowerCase().contains('tolerancia');
      return ResultadoEjecucionPunto(
        exito: false,
        error: errMsg,
        antifraudeRechazado: isAntifraude,
      );
    }
  }
}

class ResultadoEjecucionPunto {
  final bool exito;
  final String? error;
  final bool antifraudeRechazado;
  final double? distanciaActualMetros;

  ResultadoEjecucionPunto({
    required this.exito,
    this.error,
    this.antifraudeRechazado = false,
    this.distanciaActualMetros,
  });
}
