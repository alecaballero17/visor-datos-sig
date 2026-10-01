# Configuracion compartida por el lanzador y los scripts de carga.
function Get-ArquisConnectionString {
    param([switch]$LocalDB, [switch]$Start)
    if ($LocalDB) {
        $localdbExe = 'C:\Program Files\Microsoft SQL Server\160\Tools\Binn\SqlLocalDB.exe'
        if (-not (Test-Path $localdbExe)) { throw 'Instale SQL Server 2022 LocalDB o use el arranque predeterminado con Docker.' }
        if ($Start) {
            & $localdbExe start MSSQLLocalDB | Out-Host
            if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar LocalDB.' }
        }
        return 'Server=(localdb)\MSSQLLocalDB;Database=VisorDatosSIG;Integrated Security=True;TrustServerCertificate=True'
    }
    $envFile = Join-Path $PSScriptRoot '.setup/sql.env'
    if ($Start) {
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Instale Docker Desktop y active los contenedores Linux.' }
        $dockerOS = & docker info --format '{{.OSType}}'
        if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop no responde. Abra Docker Desktop y espere a que inicie.' }
        if ($dockerOS -ne 'linux') { throw 'Cambie Docker Desktop a contenedores Linux.' }
        if (-not (Test-Path $envFile)) {
            New-Item -ItemType Directory -Force (Split-Path $envFile) | Out-Null
            $password = 'Arquis1!' + [guid]::NewGuid().ToString('N')
            Set-Content -LiteralPath $envFile -Value "ARQUIS_SQL_PASSWORD=$password" -Encoding ASCII
        }
        & docker compose --project-directory $PSScriptRoot --env-file $envFile -f "$PSScriptRoot/compose.yaml" up -d sql | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar SQL Server en Docker.' }
    }
    if (-not (Test-Path $envFile)) { throw 'Ejecute primero LEVANTAR_ARQUIS.cmd para preparar SQL Server en Docker.' }
    $passwordLine = Get-Content -LiteralPath $envFile | Where-Object { $_ -like 'ARQUIS_SQL_PASSWORD=*' } | Select-Object -First 1
    if (-not $passwordLine) { throw 'Falta ARQUIS_SQL_PASSWORD en .setup/sql.env.' }
    $builder = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
    $builder["Data Source"] = '127.0.0.1,14330'
    $builder["Initial Catalog"] = 'VisorDatosSIG'
    $builder["User ID"] = 'sa'
    $builder["Password"] = $passwordLine.Substring('ARQUIS_SQL_PASSWORD='.Length)
    $builder["TrustServerCertificate"] = $true
    $builder["Connect Timeout"] = 3
    if ($Start) {
        $builder["Initial Catalog"] = 'master'
        $ready = $false
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            $probe = New-Object System.Data.SqlClient.SqlConnection $builder.ConnectionString
            try { $probe.Open(); $ready = $true; break } catch { Start-Sleep -Seconds 2 } finally { $probe.Dispose() }
        }
        if (-not $ready) { throw 'SQL Server no estuvo listo. Revise docker compose logs sql y conserve .setup/sql.env junto con el volumen.' }
        $builder["Initial Catalog"] = 'VisorDatosSIG'
    }
    return $builder.ConnectionString
}
