# Publica SÓ o app público (porta 8003) pelo Tailscale Funnel.
# Postgres (5432), Ollama (11434), n8n (5678), API interna (8002) e Streamlit (8501) NÃO são publicados.
# Uso:  .\scripts\funnel.ps1          (liga)
#       .\scripts\funnel.ps1 -Desligar
param([switch]$Desligar)

$PortaPublica = 8003

if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) {
    Write-Host "Tailscale não instalado. Baixe em https://tailscale.com/download/windows e faça login." -ForegroundColor Red
    exit 1
}

if ($Desligar) {
    tailscale funnel reset
    Write-Host "Funnel desligado." -ForegroundColor Yellow
    exit 0
}

try {
    Invoke-RestMethod "http://127.0.0.1:$PortaPublica/public/health" -TimeoutSec 3 | Out-Null
} catch {
    Write-Host "O app público não responde na porta $PortaPublica. Suba antes: .\scripts\subir_evento.ps1" -ForegroundColor Red
    exit 1
}

# Limpa qualquer publicação antiga e expõe apenas a porta pública.
tailscale funnel reset | Out-Null
tailscale funnel --bg $PortaPublica
if ($LASTEXITCODE -ne 0) {
    Write-Host "Falhou. Confira no painel do Tailscale se HTTPS e Funnel estão habilitados (veja o README)." -ForegroundColor Red
    exit 1
}
tailscale funnel status
Write-Host "`nUse a URL https://...ts.net acima como MOVE30_API_URL na Vercel (ela não muda entre reinícios)." -ForegroundColor Green
