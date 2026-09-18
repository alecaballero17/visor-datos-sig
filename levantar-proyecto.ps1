param(
    [switch]$PrepararBase,
    [switch]$ImportarCapas
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
try {
    Write-Host 'ARQUIS - Preparacion y arranque local' -ForegroundColor Cyan
    $dotnet = (Get-Command dotnet -ErrorAction SilentlyContinue).Source
    if (-not $dotnet) { $dotnet = 'C:\Program Files\dotnet\dotnet.exe' }
    if (-not (Test-Path $dotnet)) { throw 'Falta el SDK .NET 10. Consulte COMO_EJECUTAR.md, paso 1.' }
    $sdks = & $dotnet --list-sdks
    if ($LASTEXITCODE -ne 0 -or -not ($sdks -match '^10\.')) { throw 'Instale el SDK .NET 10 (el runtime solo no alcanza). Consulte COMO_EJECUTAR.md.' }
    $localdb = 'C:\Program Files\Microsoft SQL Server\160\Tools\Binn\SqlLocalDB.exe'
    if (-not (Test-Path $localdb)) { throw 'Falta SQL Server 2022 LocalDB. Consulte COMO_EJECUTAR.md, paso 1.' }
    & $localdb start MSSQLLocalDB
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar LocalDB para este usuario de Windows.' }

    $cn = New-Object System.Data.SqlClient.SqlConnection 'Server=(localdb)\MSSQLLocalDB;Database=master;Integrated Security=True;TrustServerCertificate=True'
    try {
        $cn.Open()
        $check = $cn.CreateCommand()
        $check.CommandText = "SELECT DB_ID(N'VisorDatosSIG')"
        $newDatabase = $check.ExecuteScalar() -is [DBNull]
        $needsPreparation = $newDatabase -or $PrepararBase -or $ImportarCapas
        if (-not $newDatabase) {
            $check.CommandText = "USE VisorDatosSIG; SELECT CASE WHEN COL_LENGTH('dbo.Usuarios','Email') IS NULL OR COL_LENGTH('dbo.CodigosFijos','EstadoVerificado') IS NULL OR OBJECT_ID('dbo.sp_ActualizarLoteCodigosFijos','P') IS NULL THEN 1 ELSE 0 END"
            $needsPreparation = $needsPreparation -or ($check.ExecuteScalar() -eq 1)
        }
    } finally { $cn.Dispose() }

    $hasShapes = Test-Path '03_DatosPrueba/DatosSIG_Reproj/*.shp'
    if ($ImportarCapas -and -not $hasShapes) { throw 'Copie las capas en 03_DatosPrueba/DatosSIG_Reproj. Consulte 03_DatosPrueba/README.md.' }
    if ($ImportarCapas -or ($newDatabase -and $hasShapes)) {
        $python = (Get-Command py -ErrorAction SilentlyContinue).Source
        if (-not $python) { $python = (Get-Command python -ErrorAction SilentlyContinue).Source }
        if (-not $python) { throw 'Para importar capas instale Python 3 y pyshp. Consulte COMO_EJECUTAR.md.' }
        & $python convertir-capas.py
        if ($LASTEXITCODE -ne 0) { throw 'No se pudieron convertir las capas. Revise los archivos e instale pyshp segun COMO_EJECUTAR.md.' }
    }
    if ($needsPreparation) {
        Write-Host 'Preparando la base y las relaciones espaciales. Puede tardar varios minutos.'
        & "$PSScriptRoot/preparar-base.ps1"
    } else { Write-Host 'La base ya esta preparada; se conservan los usuarios y datos.' }
    if ($newDatabase -and -not $hasShapes -and -not (Test-Path '.setup/capas.sql')) {
        Write-Warning 'La base se creo sin capas. El mapa no tendra lotes hasta importar los archivos SHP.'
    }
    & "$PSScriptRoot/iniciar.ps1"
    Write-Host 'Listo. Abra http://localhost:5180 en su navegador.' -ForegroundColor Green
    exit 0
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Consulte COMO_EJECUTAR.md y los logs en .setup.'
    exit 1
}
