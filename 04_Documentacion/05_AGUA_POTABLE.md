# Ficha de agua potable

Al seleccionar un codigo fijo o un lote en el mapa, el panel consulta los
registros asociados y muestra codigo fijo/SIG, nombre registrado, lote,
UV, manzana y coordenadas de la geometria. Un lote puede contener varios
registros; cada uno se puede ubicar desde su ficha.

Se aplica el criterio indicado por el usuario: un lote con codigo fijo
representa agua potable y se muestra con un grifo azul; un lote sin codigos
fijos representa ausencia de agua y se muestra con un grifo rojo tachado.
Se considera tanto el vinculo IdLote como la presencia espacial de un codigo
dentro del poligono. Asi un codigo vinculado a otro lote superpuesto no
produce una clasificacion contradictoria. La ficha utiliza el mismo criterio.
La consulta de disponibilidad considera todos los codigos de la base, aunque
no esten cargados en la vista actual del mapa. Las capas de lotes y codigos
fijos se muestran inicialmente. La leyenda, el mapa y las fichas utilizan
el mismo criterio. Cada lote tiene un solo simbolo, ubicado en un punto
interior. Los codigos se muestran como puntos consultables, sin duplicar
simbolos de servicio. Los simbolos por lote se muestran desde el zoom 17
para evitar que las senales de lotes vecinos se amontonen.

Las casillas **Con agua** y **Sin agua** permiten mostrar u ocultar cada
grupo de lotes de forma independiente. Ocultar Con agua oculta tambien los
puntos de codigos fijos. La leyenda se actualiza y una seleccion oculta no
deja un resaltado residual. Las respuestas antiguas de carga del mapa no
reemplazan las de una vista mas reciente.

## Informacion comprobada

El archivo `Arquis.zip` suministrado contiene las mismas capas y scripts de
base de datos del proyecto existente (comparados mediante SHA-256).
`Exp_CodigoFijo_4326.dbf` tiene 6.271 registros y los campos `Text`,
`CodF_SQL`, `CodF_SIG`, `Longi`, `Latid`, `CodFijo` y `Nombre`.
No contiene detalles de conexion, numero de medidor, lecturas, consumo,
historial ni estado operativo del servicio. La disponibilidad de agua se
clasifica segun la presencia de codigo fijo, conforme al criterio del usuario.

El esquema inicial asignaba `Estado=1` (Normal) por defecto. El script
`11_Estado_Servicio_Verificado.sql` agrega `EstadoVerificado=0` a los
registros existentes. La ficha muestra **Sin verificar** y devuelve
`estadoServicio=null` mientras el estado no este confirmado. No se
inventaron datos de medidores, conexiones o consumo. Las coordenadas de la
ficha se obtienen de la geometria, pues la documentacion original advierte
anomalias en algunos valores de `Latid`.

## API

- `GET /api/agua-potable/codigos/{id}`: ficha por IdCodigo.
- `GET /api/agua-potable/lotes/{id}`: registros asociados a un IdLote;
  devuelve una lista vacia si el lote existe y no tiene registros asociados.

Ambos endpoints incluyen `tieneAgua` segun ese criterio, requieren sesion, permiten acceso al rol Consultor y
devuelven 404 para entidades inexistentes. Son consultas; esta entrega no
incluye edicion o importacion de registros adicionales del servicio.

Para completar la informacion se requiere un registro real del proveedor de
agua potable vinculado mediante codigo fijo, con identificadores de medidor,
conexion, lecturas/fechas y estado confirmado.

Validacion: compilacion sin errores ni advertencias; inicio de sesion con
Valeria; ficha por codigo y lote; coordenadas iguales a las del mapa;
estado inicial sin confirmar; respuestas 401 y 404. JavaScript validado
sintacticamente. No se realizo revision visual por falta de navegador conectado.
