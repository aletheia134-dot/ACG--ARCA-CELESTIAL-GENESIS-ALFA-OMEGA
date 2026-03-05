# ============================================================
# INICIAR ARCA COMPLETA (JOBS + INTERFACE)
# ============================================================

param(
    [switch]$SemLog  # Se quiser rodar sem salvar logs
)

Write-Host "🚀 INICIANDO ARCA CELESTIAL" -ForegroundColor Cyan
Write-Host "==========================="

$root = "E:\Arca_Celestial_Genesis_Alfa_Omega"
cd $root

# ============================================================
# 1. MATAR JOBS ANTIGOS SE EXISTIREM
# ============================================================
Write-Host "`n🛑 Limpando jobs antigos..." -ForegroundColor Yellow
& .\scripts\parar_jobs.ps1

# ============================================================
# 2. INICIAR JOBS EM BACKGROUND
# ============================================================
Write-Host "`n🚀 Iniciando novos jobs..." -ForegroundColor Green
if ($SemLog) {
    & .\scripts\iniciar_jobs.ps1 -SemLog
} else {
    & .\scripts\iniciar_jobs.ps1
}

# ============================================================
# 3. AGUARDAR SERVIDORES INICIAREM
# ============================================================
Write-Host "`n⏳ Aguardando servidores iniciarem..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# ============================================================
# 4. VERIFICAR STATUS
# ============================================================
& .\scripts\status_jobs.ps1

# ============================================================
# 5. INICIAR INTERFACE (CORE)
# ============================================================
Write-Host "`n🟢 Iniciando interface da Arca..." -ForegroundColor Green
& .\venvs\core\Scripts\Activate.ps1

Write-Host "`n✨ ARCA PRONTA! A interface vai abrir..." -ForegroundColor Cyan
Write-Host "💡 Quando fechar a interface, os jobs continuam rodando."
Write-Host "💡 Use '.\scripts\parar_jobs.ps1' para parar tudo."

python main.py

# ============================================================
# 6. QUANDO FECHAR A INTERFACE
# ============================================================
Write-Host "`n🟡 Interface fechada. Jobs continuam rodando em background." -ForegroundColor Yellow
Write-Host "💡 Para parar tudo: .\scripts\parar_jobs.ps1"
Write-Host "💡 Para ver status: .\scripts\status_jobs.ps1"