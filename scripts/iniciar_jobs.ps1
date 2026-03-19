# ============================================================
# INICIAR JOBS DA ARCA (Background)
# ============================================================

param(
    [switch]$SemLog  # Se quiser rodar sem salvar logs
)

Write-Host "🚀 INICIANDO JOBS DA ARCA" -ForegroundColor Cyan
Write-Host "========================="

$root = "E:\Arca_Celestial_Genesis_Alfa_Omega"
cd $root

# Função para verificar se job já existe
function JobExiste($nome) {
    $jobs = Get-Job -Name $nome -ErrorAction SilentlyContinue
    return ($jobs -ne $null)
}

# ============================================================
# JOB 1: MEDIA (câmera/áudio)
# ============================================================
if (JobExiste "ArcaMedia") {
    Write-Host "📷 Job MEDIA já existe. Removendo..." -ForegroundColor Yellow
    Remove-Job -Name "ArcaMedia" -Force -ErrorAction SilentlyContinue
}

Write-Host "📷 Iniciando servidor MEDIA (porta 5001)..." -ForegroundColor Green

if ($SemLog) {
    $scriptMedia = {
        cd $using:root
        & .\venvs\media\Scripts\Activate.ps1
        Write-Host "✅ MEDIA server rodando (porta 5001)" -ForegroundColor Magenta
        uvicorn src.servidores.servidor_media:app --host 0.0.0.0 --port 5001
    }
} else {
    $scriptMedia = {
        cd $using:root
        & .\venvs\media\Scripts\Activate.ps1
        uvicorn src.servidores.servidor_media:app --host 0.0.0.0 --port 5001 *>> "$using:root\scripts\logs\media.log"
    }
}

Start-Job -Name "ArcaMedia" -ScriptBlock $scriptMedia

# ============================================================
# JOB 2: LLM (fine-tuning GPU)
# ============================================================
if (JobExiste "ArcaLLM") {
    Write-Host "🧠 Job LLM já existe. Removendo..." -ForegroundColor Yellow
    Remove-Job -Name "ArcaLLM" -Force -ErrorAction SilentlyContinue
}

Write-Host "🧠 Iniciando servidor LLM (porta 5002)..." -ForegroundColor Green

if ($SemLog) {
    $scriptLLM = {
        cd $using:root
        & .\venvs\llm\Scripts\Activate.ps1
        Write-Host "✅ LLM server rodando (porta 5002)" -ForegroundColor Magenta
        uvicorn src.servidores.servidor_llm:app --host 0.0.0.0 --port 5002
    }
} else {
    $scriptLLM = {
        cd $using:root
        & .\venvs\llm\Scripts\Activate.ps1
        uvicorn src.servidores.servidor_llm:app --host 0.0.0.0 --port 5002 *>> "$using:root\scripts\logs\llm.log"
    }
}

Start-Job -Name "ArcaLLM" -ScriptBlock $scriptLLM

# ============================================================
# JOB 3: WEB (navegador)
# ============================================================
if (JobExiste "ArcaWeb") {
    Write-Host "🌐 Job WEB já existe. Removendo..." -ForegroundColor Yellow
    Remove-Job -Name "ArcaWeb" -Force -ErrorAction SilentlyContinue
}

Write-Host "🌐 Iniciando servidor WEB (porta 5003)..." -ForegroundColor Green

if ($SemLog) {
    $scriptWeb = {
        cd $using:root
        & .\venvs\web\Scripts\Activate.ps1
        Write-Host "✅ WEB server rodando (porta 5003)" -ForegroundColor Magenta
        uvicorn src.servidores.servidor_web:app --host 0.0.0.0 --port 5003
    }
} else {
    $scriptWeb = {
        cd $using:root
        & .\venvs\web\Scripts\Activate.ps1
        uvicorn src.servidores.servidor_web:app --host 0.0.0.0 --port 5003 *>> "$using:root\scripts\logs\web.log"
    }
}

Start-Job -Name "ArcaWeb" -ScriptBlock $scriptWeb

# ============================================================
# VERIFICAR SE JOBS INICIARAM
# ============================================================
Start-Sleep -Seconds 3

Write-Host "`n📊 STATUS DOS JOBS:" -ForegroundColor Cyan
Get-Job | Format-Table Id, Name, State, HasMoreData -AutoSize

Write-Host "`n✅ JOBS INICIADOS!" -ForegroundColor Green
Write-Host "💡 Use '.\scripts\status_jobs.ps1' para ver status"
Write-Host "💡 Use '.\scripts\parar_jobs.ps1' para parar tudo"