import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:movil/modules/mapa/services/tracking_gps_service.dart';
import 'package:movil/modules/mapa/views/widgets/formulario_cierre_orden_modal.dart';

void main() {
  testWidgets('Sin foto ni comentario valida lectura y continúa hasta GPS', (
    tester,
  ) async {
    dotenv.loadFromString(envString: 'API_URL=http://localhost:5080/api');
    final tracking = TrackingGpsService();
    // El modo de ensayo evita invocar GPS nativo o enviar la orden real.
    tracking.isSimulacionActiva = true;
    addTearDown(tracking.limpiarSesion);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: FormularioCierreOrdenModal(
            rutaActiva: const {'id': 1, 'tipo': 'Corte'},
            objetivoActual: const {
              'id': 2,
              'latitud': -16.397,
              'longitud': -60.96,
            },
          ),
        ),
      ),
    );
    final confirmar = find.text('Confirmar Corte');
    await tester.ensureVisible(confirmar);
    await tester.tap(confirmar);
    await tester.pumpAndSettle();
    expect(
      find.textContaining('Ingrese una lectura numérica válida'),
      findsOneWidget,
    );

    final lectura = find.byType(TextField).first;
    await tester.ensureVisible(lectura);
    await tester.enterText(lectura, '482.50');
    await tester.ensureVisible(confirmar);
    await tester.tap(confirmar);
    await tester.pumpAndSettle();
    // Sin foto ni comentario se llega a la comprobación GPS; no se bloquea por evidencia.
    expect(find.textContaining('Modo de ensayo:'), findsOneWidget);
    expect(find.textContaining('Es obligatorio adjuntar'), findsNothing);
  });
}
