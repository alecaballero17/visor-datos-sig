from cli.modules.services.control import menu_servicio

from . import nginx

# Acciones comunes de servicio (iniciar, detener, logs en vivo...) + propias de nginx
MENU = menu_servicio("nginx", "nginx (proxy inverso)", orden=50)
MENU.descripcion = "Dominios/subdominios para visor y API, HTTPS (Let's Encrypt) y proxy inverso"
MENU.agregar("dominios", "Configurar dominios y HTTPS", nginx.dominios, "visor + subdominio de la API")
MENU.agregar("aplicar", "Aplicar (nginx + certificado + servicios)", nginx.aplicar)
MENU.agregar("urls", "Ver URLs publicas", nginx.resumen_urls)
MENU.agregar("dns", "Comprobar DNS de los dominios", nginx.comprobar_dns)
MENU.agregar("https", "Emitir/ampliar certificado Let's Encrypt", nginx.certificado)
MENU.agregar("certificado", "Estado del certificado", nginx.estado_certificado)
MENU.agregar("renovar-prueba", "Probar renovacion (dry-run)", nginx.renovar_prueba)
MENU.agregar("descargar", "Instalar nginx", nginx.instalar_binarios)
MENU.agregar("config", "Generar configuracion", nginx.escribir_config)
MENU.agregar("preview", "Vista previa de la configuracion", nginx.vista_previa)
MENU.agregar("ver-config", "Ver configuracion instalada", nginx.ver_config)
MENU.agregar("probar", "Probar configuracion (nginx -t)", nginx.probar)
MENU.agregar("recargar", "Recargar sin cortar conexiones", nginx.recargar)
MENU.agregar("firewall", "Abrir puertos en el firewall", nginx.firewall)
MENU.agregar("quitar-config", "Eliminar configuracion", nginx.quitar_config)
