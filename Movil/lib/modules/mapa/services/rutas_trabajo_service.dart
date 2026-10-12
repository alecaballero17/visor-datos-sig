import '../../../../core/network/api_provider.dart';

class RutasTrabajoService {
  final ApiProvider _api = ApiProvider();

  Future<List<dynamic>> obtenerRutasAsignadas({String? operario}) async {
    try {
      final Map<String, dynamic> params = {};
      if (operario != null && operario.isNotEmpty) {
        params['operario'] = operario;
      }
      final res = await _api.get('/rutas-trabajo/asignadas', queryParameters: params.isNotEmpty ? params : null);
      if (res is List) return res;
      return [];
    } catch (e) {
      return [];
    }
  }

  Future<Map<String, dynamic>?> obtenerDetalleRuta(int rutaId) async {
    try {
      final res = await _api.get('/rutas-trabajo/$rutaId');
      if (res is Map<String, dynamic>) return res;
      return null;
    } catch (e) {
      return null;
    }
  }

  Future<bool> iniciarRuta(int rutaId) async {
    try {
      await _api.put('/rutas-trabajo/$rutaId/iniciar');
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<bool> ejecutarAccionPunto({
    required int rutaId,
    required int puntoId,
    String? observaciones,
  }) async {
    try {
      final res = await _api.put(
        '/rutas-trabajo/$rutaId/puntos/$puntoId/ejecutar',
        data: {
          'observaciones': observaciones ?? 'Operativo ejecutado en campo con éxito.',
        },
      );
      return res != null;
    } catch (e) {
      return false;
    }
  }
}
