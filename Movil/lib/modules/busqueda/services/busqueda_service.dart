import '../../../../core/network/api_provider.dart';

class BusquedaService {
  final ApiProvider _api = ApiProvider();

  Future<List<dynamic>> buscar(String query) async {
    try {
      final response = await _api.get('/search?q=$query');
      return response.data as List<dynamic>;
    } catch (e) {
      throw Exception('Error al buscar: $e');
    }
  }
}
