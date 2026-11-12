# Abre o Docker Desktop e liga o n8n (a IA depende dele).
# Uso:  .\scripts\abrir_docker.ps1
#
# O Docker Desktop e aberto pelo explorer.exe, como num clique no icone.
# Aberto direto de outro terminal (ou de uma ferramenta), ele vira filho daquele processo
# e pode morrer junto quando o terminal fecha: a janela abre, mas o motor (WSL) nao sobe.
param([int]$EsperaS = 240)

function MotorOk { docker info *> $null; return $LASTEXITCODE -eq 0 }

if (MotorOk) {
    Write-Host "[ok] Docker ja estava rodando" -ForegroundColor Green
} else {
    $exe = @(
        "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $exe) { Write-Host "[!!] Docker Desktop nao encontrado." -ForegroundColor Red; exit 1 }

    Write-Host "Abrindo o Docker Desktop..."
    Start-Process explorer.exe -ArgumentList "`"$exe`""
    $fim = (Get-Date).AddSeconds($EsperaS)
    while (-not (MotorOk) -and (Get-Date) -lt $fim) { Start-Sleep 3 }
    if (-not (MotorOk)) {
        Write-Host "[!!] O motor do Docker nao subiu em $EsperaS s. Feche o Docker (Quit), rode 'wsl --shutdown' e tente de novo; se nao resolver, reinicie o PC." -ForegroundColor Red
        exit 1
    }
    Write-Host "[ok] Docker rodando" -ForegroundColor Green
}

# n8n: liga o container se estiver parado e espera responder.
$estado = docker inspect -f "{{.State.Running}}" n8n 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "[!!] Container 'n8n' nao existe." -ForegroundColor Red; exit 1 }
if ($estado -ne "true") { docker start n8n | Out-Null }
$fim = (Get-Date).AddSeconds(90)
do {
    try { Invoke-WebRequest "http://127.0.0.1:5678/healthz" -TimeoutSec 3 -UseBasicParsing | Out-Null; $n8n = $true }
    catch { $n8n = $false; Start-Sleep 3 }
} until ($n8n -or (Get-Date) -gt $fim)
if ($n8n) { Write-Host "[ok] n8n respondendo" -ForegroundColor Green }
else { Write-Host "[!!] n8n nao respondeu em 90 s (docker logs n8n)." -ForegroundColor Red; exit 1 }
