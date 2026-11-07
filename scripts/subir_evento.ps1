# Sobe tudo para o dia do evento, cada serviço numa janela própria.
# Pré-requisitos ligados antes: PostgreSQL e Docker (n8n). O Ollama roda como app do Windows.
$Raiz = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Raiz ".venv\Scripts\python.exe"

function Testar($nome, $url) {
    try { Invoke-WebRequest $url -TimeoutSec 3 -UseBasicParsing | Out-Null; Write-Host "[ok] $nome" -ForegroundColor Green }
    catch { Write-Host "[!!] $nome não responde em $url" -ForegroundColor Red }
}

# Mostra qual banco vai ser usado (no evento tem que ser move30_evento).
$Banco = (Get-Content (Join-Path $Raiz ".env") | Where-Object { $_ -like "DB_NAME=*" }) -replace "^DB_NAME=", ""
if ($Banco -eq "move30_evento") { Write-Host "[ok] Banco: $Banco (evento)" -ForegroundColor Green }
else { Write-Host "[!!] Banco: $Banco (TESTES). No dia do evento rode antes: .venv\Scripts\python.exe -m scripts.preparar_evento --ativar" -ForegroundColor Yellow }

Testar "Ollama" "http://127.0.0.1:11434/api/tags"
Testar "n8n" "http://127.0.0.1:5678/healthz"

# API interna: rede local (ESP32, dashboards Streamlit). Nunca vai para o Funnel.
Start-Process powershell -WorkingDirectory $Raiz -ArgumentList "-NoExit", "-Command", "& '$Py' -m uvicorn backend.main:app --host 0.0.0.0 --port 8002"
# App público: só escuta em 127.0.0.1; quem publica é o Funnel.
Start-Process powershell -WorkingDirectory $Raiz -ArgumentList "-NoExit", "-Command", "& '$Py' -m uvicorn backend.public_app:app --host 127.0.0.1 --port 8003"
# Dashboards locais (TV / equipe).
Start-Process powershell -WorkingDirectory $Raiz -ArgumentList "-NoExit", "-Command", "& '$Py' -m streamlit run Dashboard\app.py"

Start-Sleep -Seconds 6
Testar "API interna" "http://127.0.0.1:8002/db-health"
Testar "App público" "http://127.0.0.1:8003/public/health"
Write-Host "`nAgora rode: .\scripts\funnel.ps1" -ForegroundColor Cyan
