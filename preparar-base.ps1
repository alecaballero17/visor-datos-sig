$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$localdb = 'C:\Program Files\Microsoft SQL Server\160\Tools\Binn\SqlLocalDB.exe'
if (-not (Test-Path $localdb)) { throw 'Instale SQL Server 2022 LocalDB.' }
& $localdb start MSSQLLocalDB
if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar LocalDB.' }
$cn = New-Object System.Data.SqlClient.SqlConnection 'Server=(localdb)\MSSQLLocalDB;Database=master;Integrated Security=True;TrustServerCertificate=True'
$cn.Open()
try {
    $check = $cn.CreateCommand()
    $check.CommandText = "SELECT DB_ID(N'VisorDatosSIG')"
    if ($check.ExecuteScalar() -is [DBNull]) {
        $scripts = @('01_CrearBD.sql', '04_Actualizar_CodigosFijos_Estado.sql', '05_Optimizar_Relacion_CodigoFijo_Lote.sql', '06_Agregar_Nombre_Vias.sql', '07_Roles_Usuarios_Menu.sql', '08_MenuOpciones_UsuarioMenu.sql', '09_Arquis_Alfa.sql')
        foreach ($file in $scripts) {
            Write-Host "Ejecutando $file"
            $sql = Get-Content "02_BaseDatos/$file" -Raw -Encoding UTF8
            foreach ($batch in [regex]::Split($sql, '(?im)^\s*GO\s*\r?$')) {
                if (-not $batch.Trim()) { continue }
                $cmd = $cn.CreateCommand()
                $cmd.CommandTimeout = 600
                $cmd.CommandText = $batch
                [void]$cmd.ExecuteNonQuery()
            }
        }
    } else { Write-Host 'La base ya existe; se conserva su esquema y contenido.' }
    if (Test-Path '.setup/capas.sql') {
        $cmd = $cn.CreateCommand()
        $cmd.CommandTimeout = 600
        $cmd.CommandText = Get-Content '.setup/capas.sql' -Raw -Encoding UTF8
        [void]$cmd.ExecuteNonQuery()
    }
    $cmd = $cn.CreateCommand()
    $cmd.CommandTimeout = 600
    $sql = (Get-Content '02_BaseDatos/10_Asociacion_Indices_Espaciales.sql' -Raw -Encoding UTF8) + "`n" + (Get-Content '02_BaseDatos/11_Estado_Servicio_Verificado.sql' -Raw -Encoding UTF8) + "`n" + (Get-Content '02_BaseDatos/12_Indice_Codigos_Agua.sql' -Raw -Encoding UTF8)
    foreach ($batch in [regex]::Split($sql, '(?im)^\s*GO\s*\r?$')) {
        if (-not $batch.Trim()) { continue }
        $cmd.CommandText = $batch
        [void]$cmd.ExecuteNonQuery()
    }
    $sql = Get-Content '02_BaseDatos/13_Registro_Email.sql' -Raw -Encoding UTF8
    foreach ($batch in [regex]::Split($sql, '(?im)^\s*GO\s*\r?$')) {
        if (-not $batch.Trim()) { continue }
        $cmd.CommandText = $batch
        [void]$cmd.ExecuteNonQuery()
    }
    $cmd.CommandText = 'USE VisorDatosSIG; EXEC dbo.sp_ActualizarLoteCodigosFijos;'
    [void]$cmd.ExecuteNonQuery()
    Write-Host 'Base local preparada.'
} finally { $cn.Dispose() }
