/// Estados compartidos por bandeja, navegación y recuperación de cierres.
bool puntoAtendido(Map<String, dynamic> punto) => const {
  'completado', 'ejecutado', 'observado', 'omitido',
}.contains(punto['estado']?.toString().toLowerCase());

List<Map<String, dynamic>> ordenarPuntos(Iterable<dynamic> puntos) {
  final resultado = puntos.map((p) => p is Map<String, dynamic> ? p : Map<String, dynamic>.from(p as Map)).toList();
  resultado.sort((a, b) => ((a['orden'] as num?) ?? 0).compareTo((b['orden'] as num?) ?? 0));
  return resultado;
}

Map<String, dynamic>? siguientePunto(Iterable<dynamic> puntos) {
  for (final punto in ordenarPuntos(puntos)) {
    if (!puntoAtendido(punto)) return punto;
  }
  return null;
}
