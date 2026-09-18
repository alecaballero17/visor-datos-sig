# Registro de usuarios

En la pantalla de login, **Registrar usuario** muestra un formulario con
nombre (2 a 120 caracteres), email (hasta 254 caracteres) y contrasena
(8 a 128 caracteres). Tras crear la cuenta, se vuelve al login con el email
completado. Los usuarios existentes pueden seguir usando su nombre de usuario.

`POST /api/autenticacion/registrar` recibe `nombre`, `email` y `password`.
Responde 201 al crear una cuenta, 400 por datos invalidos y 409 si el email
ya existe. Las nuevas cuentas reciben exclusivamente el rol Consultor;
no se aceptan roles ni permisos administrativos desde el formulario.
`POST /api/autenticacion/iniciar` permite ingresar con email o usuario.

La migracion `13_Registro_Email.sql` agrega Email e indice unico filtrado.
Los usuarios existentes mantienen su login, contrasena y roles; su Email
queda vacio hasta que exista una funcion de edicion. Se asigna a cada cuenta
nueva un login interno unico. El email se normaliza y la contrasena se
almacena con PBKDF2-SHA256, sal aleatoria de 32 bytes y 210.000 iteraciones.
La transaccion incluye cuenta, rol y permisos de consulta del menu.

Validado: rechazo de datos invalidos; registro correcto; rechazo de email
duplicado incluso con mayusculas; login por email; rechazo de contrasena
incorrecta; rol Consultor aunque se envie otro rol en el JSON; acceso
existente de Valeria; formulario presente en la vista servida. La cuenta
temporal usada para validar se elimina despues de las pruebas.

No se realizo revision visual automatizada: no hay navegador conectado.
