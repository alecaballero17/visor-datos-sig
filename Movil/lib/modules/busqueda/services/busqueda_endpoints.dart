class BusquedaEndpoints {
  static String buscar(String texto, {String? capa, int tamano = 25}) {
    String url = '/busqueda?texto=${Uri.encodeComponent(texto)}&tamano=$tamano';
    if (capa != null && capa.isNotEmpty) {
      url += '&capa=${Uri.encodeComponent(capa)}';
    }
    return url;
  }
}
