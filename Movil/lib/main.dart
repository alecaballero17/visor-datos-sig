import 'dart:ui';
import 'modules/auth/models/sesion_usuario.dart';
import 'modules/mapa/services/tracking_gps_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'modules/auth/views/screens/flujo_principal/auth_pantalla_inicio.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: ".env.example");
  TrackingGpsService();
  SesionUsuario.actual.addListener(() {
    if (SesionUsuario.actual.value == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        appNavigatorKey.currentState?.pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const AuthPantallaInicio()),
          (_) => false,
        );
      });
    }
  });
  runApp(const MyApp());
}

final appNavigatorKey = GlobalKey<NavigatorState>();

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final tracking = TrackingGpsService();
    tracking.actualizarPrimerPlano(state == AppLifecycleState.resumed);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    TrackingGpsService().detenerTransmision();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: appNavigatorKey,
      title: 'GeoIT Operaciones',
      debugShowCheckedModeBanner: false,
      // Habilita el arrastre fluido (smooth drag) con Mouse, Touch, Stylus y Trackpad en todas las plataformas
      scrollBehavior: const MaterialScrollBehavior().copyWith(
        dragDevices: {
          PointerDeviceKind.mouse,
          PointerDeviceKind.touch,
          PointerDeviceKind.stylus,
          PointerDeviceKind.trackpad,
        },
      ),
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.cyanAccent,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const AuthPantallaInicio(),
    );
  }
}
