param([switch]$LocalDB)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
. "$PSScriptRoot/conexion-base.ps1"
if (-not $env:ConnectionStrings__DefaultConnection -or $LocalDB) {
    $env:ConnectionStrings__DefaultConnection = Get-ArquisConnectionString -LocalDB:$LocalDB
}
$dotnet = (Get-Command dotnet -ErrorAction SilentlyContinue).Source
if (-not $dotnet) { $dotnet = 'C:\Program Files\dotnet\dotnet.exe' }
if (-not (Test-Path $dotnet)) { throw 'Instale el SDK de .NET 10.' }
New-Item -ItemType Directory -Force .setup | Out-Null
foreach ($project in @('Backend', 'Frontend')) {
    $port = if ($project -eq 'Backend') { 5080 } else { 5180 }
    $response = $null
    try { $response = Invoke-WebRequest "http://localhost:$port/$(if ($project -eq 'Backend') { 'health' })" -UseBasicParsing -TimeoutSec 3 } catch { }
    if ($response) {
        $expected = if ($project -eq 'Backend') { 'Arquis.Backend' } else { 'Arquis' }
        if ($response.Content -notmatch [regex]::Escape($expected)) { throw "El puerto $port pertenece a otra aplicacion." }
        Write-Host "Arquis.$project ya esta en ejecucion."
        continue
    }
    $probe = New-Object System.Net.Sockets.TcpClient
    try {
        $connection = $probe.ConnectAsync('127.0.0.1', $port)
        if ($connection.Wait(1000) -and $probe.Connected) { throw "El puerto $port esta ocupado pero Arquis.$project no responde. Revise el proceso antes de continuar." }
    } catch [System.AggregateException] { } finally { $probe.Dispose() }
    & $dotnet build "src/Arquis.$project" --nologo
    if ($LASTEXITCODE -ne 0) { throw "No se pudo compilar Arquis.$project." }
    $process = Start-Process -FilePath $dotnet -ArgumentList @('run', '--no-build', '--project', "src/Arquis.$project", '--launch-profile', 'http') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput "$PSScriptRoot/.setup/$project.log" -RedirectStandardError "$PSScriptRoot/.setup/$project.error.log" -PassThru
    $process.Id | Set-Content ".setup/$project.pid"
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        $process.Refresh()
        if ($process.HasExited) { throw "Arquis.$project termino inesperadamente. Revise .setup/$project.error.log y .setup/$project.log." }
        try {
            $response = Invoke-WebRequest "http://localhost:$port/$(if ($project -eq 'Backend') { 'health' })" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "Arquis.$project no respondio. Revise sus logs en .setup." }
}
Write-Host 'Visor: http://localhost:5180'
Write-Host 'API: http://localhost:5080/health'
Write-Host 'Usuario inicial: admin / Admin123!'
