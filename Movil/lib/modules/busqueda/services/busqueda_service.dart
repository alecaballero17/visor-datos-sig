import '../../../../core/network/api_provider.dart';

class BusquedaService {
  final ApiProvider _api = ApiProvider();

  Future<List<dynamic>> buscar(String query, {String? capa}) async {
    try {
      final q = query.trim();
      if (q.isEmpty) return [];

      String endpoint = '/busqueda?texto=${Uri.encodeComponent(q)}&tamano=30';
      if (capa != null && capa.isNotEmpty) {
        endpoint += '&capa=${Uri.encodeComponent(capa)}';
      }

      final response = await _api.get(endpoint);
      if (response is List) {
        return response;
      }
      return [];
    } catch (e) {
      throw Exception('Error al buscar en el servidor: $e');
    }
  }
}
