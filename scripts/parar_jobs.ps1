# ============================================================
# PARAR JOBS DA ARCA
# ============================================================

Write-Host "🛑 PARANDO JOBS DA ARCA" -ForegroundColor Cyan
Write-Host "======================="

$jobs = Get-Job

if ($jobs.Count -eq 0) {
    Write-Host "❌ Nenhum job rodando" -ForegroundColor Red
    exit
}

foreach ($job in $jobs) {
    Write-Host "Parando $($job.Name)..." -NoNewline
    Stop-Job -Job $job
    Remove-Job -Job $job
    Write-Host " ✅" -ForegroundColor Green
}

Write-Host "`n✅ TODOS OS JOBS PARADOS" -ForegroundColor Green