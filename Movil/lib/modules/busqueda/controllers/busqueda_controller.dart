import 'package:flutter/material.dart';
import '../services/busqueda_service.dart';

class BusquedaController {
  final BusquedaService _busquedaService = BusquedaService();
  final TextEditingController searchCtrl = TextEditingController();
  
  bool isCargando = false;
  List<dynamic> resultados = [];
  String? errorMessage;
  String capaFiltro = ''; // '' = todas, 'manzanas', 'lotes', 'codigosfijos', 'vias'

  Future<void> buscar(String query, Function(VoidCallback) actualizar) async {
    final q = query.trim();
    if (q.isEmpty) {
      actualizar(() {
        resultados = [];
        errorMessage = null;
        isCargando = false;
      });
      return;
    }

    actualizar(() {
      isCargando = true;
      errorMessage = null;
    });

    try {
      final data = await _busquedaService.buscar(q, capa: capaFiltro.isEmpty ? null : capaFiltro);
      actualizar(() {
        isCargando = false;
        resultados = data;
        if (data.isEmpty) {
          errorMessage = 'No se encontraron resultados para "$q".';
        }
      });
    } catch (e) {
      actualizar(() {
        isCargando = false;
        errorMessage = 'No se pudo conectar con el servicio de búsqueda: ${e.toString().replaceAll('Exception: ', '')}';
      });
    }
  }

  void cambiarCapaFiltro(String nuevaCapa, Function(VoidCallback) actualizar) {
    capaFiltro = nuevaCapa;
    if (searchCtrl.text.isNotEmpty) {
      buscar(searchCtrl.text, actualizar);
    } else {
      actualizar(() {});
    }
  }

  void dispose() {
    searchCtrl.dispose();
  }
}
