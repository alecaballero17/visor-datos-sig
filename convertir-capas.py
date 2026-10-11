"""Genera SQL de las capas incluidas; requiere pyshp."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / '.setup/pythonlibs'))
import shapefile

def coordinates(points):
    return ','.join(f'{p[0]:.17g} {p[1]:.17g}' for p in points)

def geometry_wkt(geometry):
    kind = geometry['type']
    points = geometry['coordinates']
    if kind == 'Point':
        return f'POINT({coordinates([points])})'
    if kind == 'MultiPoint':
        return f'MULTIPOINT({coordinates(points)})'
    if kind == 'LineString':
        return f'LINESTRING({coordinates(points)})'
    if kind in ('Polygon', 'MultiLineString'):
        parts = ','.join('(' + coordinates(part) + ')' for part in points)
        return f'{kind.upper()}({parts})'
    if kind == 'MultiPolygon':
        polygons = ','.join('(' + ','.join('(' + coordinates(ring) + ')' for ring in polygon) + ')' for polygon in points)
        return f'MULTIPOLYGON({polygons})'
    raise ValueError(f'Geometria no soportada: {kind}')

def literal(value, length=None):
    if value is None or value == '':
        return 'NULL'
    if isinstance(value, (int, float)):
        return str(value)
    value = str(value)
    if length:
        value = value[:length]
    return "N'" + value.replace("'", "''") + "'"

layers = [
    ('Manzanas', 'Exp_MapaBase_MZA', [('IdOrigen', 'Id', None), ('UV_MZA', 'UV_MZA', 20), ('UV', 'UV', 15), ('MZA', 'MZA', 10)]),
    ('Lotes', 'Exp_MapaBase_LOTES', [('IdOrigen', 'Id', None), ('NroLote', 'NroLote', 15)]),
    ('CodigosFijos', 'Exp_CodigoFijo', [('CodF_SQL', 'CodF_SQL', None), ('CodF_SIG', 'CodF_SIG', 25), ('CodFijo', 'CodFijo', None), ('Nombre', 'Nombre', 120), ('Longitud', 'Longi', None), ('Latitud', 'Latid', None)]),
    ('Vias', 'Exp_MapaBase_VIAS', [('OBJECTID', 'OBJECTID', None), ('Nombre', 'Nombre', 40), ('TipoVia', 'type', 30), ('OSMID', 'OSMID', 20)]),
]
# Verificar todas las capas antes de escribir un archivo SQL parcial.
for _, filename, _ in layers:
    folder = root / '03_DatosPrueba/DatosSIG_Reproj'
    if not (folder / (filename + '_4326.shp')).exists():
        folder = root / '03_DatosPrueba'
    missing = [str(folder / (filename + '_4326' + ext))
               for ext in ('.shp', '.shx', '.dbf', '.prj')
               if not (folder / (filename + '_4326' + ext)).exists()]
    if missing:
        raise SystemExit('Faltan archivos de la capa: ' + ', '.join(missing))
sqlcmd_batches = '--sqlcmd-batches' in sys.argv
(root / '.setup').mkdir(exist_ok=True)
sql_output = root / ('.setup/capas-linux.sql' if sqlcmd_batches else '.setup/capas.sql')
with sql_output.open('w', encoding='utf-8') as output:
    output.write('USE VisorDatosSIG; SET NOCOUNT ON; SET XACT_ABORT ON;\n')
    for table, filename, columns in layers:
        path = root / '03_DatosPrueba/DatosSIG_Reproj' / (filename + '_4326.shp')
        if not path.exists():
            path = root / '03_DatosPrueba' / (filename + '_4326.shp')
        cpg = path.with_suffix('.cpg')
        if not cpg.exists():
            cpg = path.with_suffix('.CPG')
        encoding = cpg.read_text().strip() if cpg.exists() else 'utf-8'
        if encoding.isdigit():
            encoding = 'cp' + encoding
        reader = shapefile.Reader(str(path), encoding=encoding)
        if sqlcmd_batches:
            output.write(f'CREATE TABLE #ArquisCarga (Activa bit);\nINSERT #ArquisCarga SELECT CASE WHEN EXISTS(SELECT 1 FROM dbo.{table}) THEN 0 ELSE 1 END;\nBEGIN TRANSACTION;\nGO\n')
        else:
            output.write(f'IF NOT EXISTS (SELECT 1 FROM dbo.{table}) BEGIN\nBEGIN TRANSACTION;\n')
        count = 0
        for feature in reader.iterShapeRecords():
            data = feature.record.as_dict()
            wkt = geometry_wkt(feature.shape.__geo_interface__)
            values = [literal(data.get(source), length) for _, source, length in columns]
            values.append(f'geometry::STGeomFromText({literal(wkt)},4326).MakeValid()')
            names = ','.join('[' + name + ']' for name, _, _ in columns) + ',Geom'
            if sqlcmd_batches and count % 100 == 0:
                output.write('IF EXISTS(SELECT 1 FROM #ArquisCarga WHERE Activa=1) BEGIN\n')
            output.write(f'INSERT dbo.{table}({names}) VALUES({",".join(values)});\n')
            count += 1
            if sqlcmd_batches and count % 100 == 0:
                output.write('END;\nGO\n')
        if sqlcmd_batches:
            if count % 100:
                output.write('END;\nGO\n')
            output.write('COMMIT; DROP TABLE #ArquisCarga;\nGO\n')
        else:
            output.write('COMMIT; END;\n')
        print(f'{table}: {count} registros')
