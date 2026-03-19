# ============================================================
# STATUS DOS JOBS DA ARCA
# ============================================================

Write-Host "📊 STATUS DOS JOBS" -ForegroundColor Cyan
Write-Host "=================="

$jobs = Get-Job

if ($jobs.Count -eq 0) {
    Write-Host "❌ Nenhum job rodando" -ForegroundColor Red
    exit
}

foreach ($job in $jobs) {
    $cor = if ($job.State -eq "Running") { "Green" } else { "Red" }
    Write-Host "$($job.Name): " -NoNewline
    Write-Host "$($job.State)" -ForegroundColor $cor
    
    # Últimas linhas do log
    if ($job.Name -eq "ArcaMedia") { $log = "scripts\logs\media.log" }
    elseif ($job.Name -eq "ArcaLLM") { $log = "scripts\logs\llm.log" }
    elseif ($job.Name -eq "ArcaWeb") { $log = "scripts\logs\web.log" }
    
    if (Test-Path $log) {
        $ultimas = Get-Content $log -Tail 2 -ErrorAction SilentlyContinue
        if ($ultimas) {
            Write-Host "  Último log:" -ForegroundColor Gray
            $ultimas | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        }
    }
}

# Testar conexões
Write-Host "`n🔌 TESTANDO CONEXÕES:" -ForegroundColor Cyan

try {
    $media = Invoke-RestMethod -Uri "http://localhost:5001/status" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  MEDIA: ✅" -ForegroundColor Green
} catch {
    Write-Host "  MEDIA: ❌" -ForegroundColor Red
}

try {
    $llm = Invoke-RestMethod -Uri "http://localhost:5002/status" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  LLM: ✅" -ForegroundColor Green
    if ($llm.gpu) { Write-Host "    GPU disponível" -ForegroundColor Yellow }
} catch {
    Write-Host "  LLM: ❌" -ForegroundColor Red
}

try {
    $web = Invoke-RestMethod -Uri "http://localhost:5003/status" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  WEB: ✅" -ForegroundColor Green
} catch {
    Write-Host "  WEB: ❌" -ForegroundColor Red
}