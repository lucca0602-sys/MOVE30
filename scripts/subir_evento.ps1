# Sobe tudo para o dia do evento, cada serviço numa janela própria.
# Pré-requisito: PostgreSQL ligado. O Docker e o n8n este script abre sozinho; o Ollama roda como app do Windows.
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
# Abre o Docker (pelo explorer, para não morrer junto com este terminal) e liga o n8n.
& (Join-Path $PSScriptRoot "abrir_docker.ps1")

# Cada serviço roda num laço: se cair (erro, falta de memória), religa sozinho em 3 s.
# Para parar de vez, feche a janela dele.
function Subir($titulo, $argumentos) {
    $laco = "`$Host.UI.RawUI.WindowTitle = 'MOVE30 - $titulo'; while (`$true) { & '$Py' $argumentos; Write-Host '[$titulo] parou; religando em 3 s (feche a janela para encerrar)' -ForegroundColor Yellow; Start-Sleep 3 }"
    Start-Process powershell -WorkingDirectory $Raiz -ArgumentList "-NoExit", "-Command", $laco
}

# API interna: rede local (ESP32, dashboards Streamlit). Nunca vai para o Funnel.
Subir "API interna" "-m uvicorn backend.main:app --host 0.0.0.0 --port 8002"
# App público: só escuta em 127.0.0.1; quem publica é o Funnel.
Subir "App publico" "-m uvicorn backend.public_app:app --host 127.0.0.1 --port 8003"
# Dashboards locais (TV / equipe).
Subir "Streamlit" "-m streamlit run Dashboard\app.py"
# Cópia na nuvem (Neon): /dash e /geral seguem no ar se o PC ou o Funnel cair. Republica a cada 2 min.
if (Get-Content (Join-Path $Raiz ".env") | Where-Object { $_ -match "^ARQUIVO_DATABASE_URL=." }) {
    Subir "Copia nuvem" "-m scripts.publicar_resultados --publicar --loop 120 --banco $Banco"
} else {
    Write-Host "[!!] Sem ARQUIVO_DATABASE_URL no .env: se o PC cair, os links do QR param." -ForegroundColor Yellow
}

Start-Sleep -Seconds 6
Testar "API interna" "http://127.0.0.1:8002/db-health"
Testar "App público" "http://127.0.0.1:8003/public/health"
Write-Host "`nAgora rode: .\scripts\funnel.ps1" -ForegroundColor Cyan
