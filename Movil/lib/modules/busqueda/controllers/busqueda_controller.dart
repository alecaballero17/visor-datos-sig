import 'package:flutter/material.dart';
import '../services/busqueda_service.dart';

class BusquedaController {
  final BusquedaService _busquedaService = BusquedaService();
  final TextEditingController searchCtrl = TextEditingController();
  
  bool isCargando = false;
  List<dynamic> resultados = [];
  String? errorMessage;

  Future<void> buscar(String query, Function(VoidCallback) actualizar) async {
    if (query.isEmpty) {
      actualizar(() {
        resultados = [];
        errorMessage = null;
      });
      return;
    }

    actualizar(() {
      isCargando = true;
      errorMessage = null;
    });

    try {
      final data = await _busquedaService.buscar(query);
      actualizar(() {
        isCargando = false;
        resultados = data;
      });
    } catch (e) {
      actualizar(() {
        isCargando = false;
        errorMessage = e.toString().replaceAll('Exception: ', '');
      });
    }
  }

  void dispose() {
    searchCtrl.dispose();
  }
}
