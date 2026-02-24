# Quick start script for NL → API Orchestrator (PowerShell)

Write-Host "🚀 Starting NL → API Orchestrator..." -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "📝 Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
}

Write-Host "🐳 Building and starting Docker services..." -ForegroundColor Cyan
docker compose up -d --build

Write-Host ""
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Cyan
Write-Host ""

# Wait for orchestrator
Write-Host "Checking orchestrator..." -ForegroundColor Yellow
$orchestratorReady = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Orchestrator is ready" -ForegroundColor Green
            $orchestratorReady = $true
            break
        }
    }
    catch {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
    }
}

if (-not $orchestratorReady) {
    Write-Host ""
    Write-Host "⚠️  Orchestrator didn't start in time. Check logs with: docker compose logs orchestrator" -ForegroundColor Yellow
}

# Wait for vLLM (this takes longer)
Write-Host ""
Write-Host "Checking vLLM (this may take 2-5 minutes)..." -ForegroundColor Yellow
$vllmReady = $false
for ($i = 1; $i -le 150; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ vLLM is ready" -ForegroundColor Green
            $vllmReady = $true
            break
        }
    }
    catch {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
    }
}

if (-not $vllmReady) {
    Write-Host ""
    Write-Host "⚠️  vLLM didn't start in time. Check logs with: docker compose logs vllm" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✨ All services are ready!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Service URLs:" -ForegroundColor Cyan
Write-Host "  - Orchestrator API: http://localhost:8080"
Write-Host "  - Orchestrator Health: http://localhost:8080/health"
Write-Host "  - Prometheus: http://localhost:9090"
Write-Host "  - Grafana: http://localhost:3000 (admin/admin)"
Write-Host "  - Jaeger: http://localhost:16686"
Write-Host "  - Traefik Dashboard: http://localhost:8090"
Write-Host ""
Write-Host "🧪 Test the orchestrator:" -ForegroundColor Cyan
Write-Host '  $body = @{query="Open urgent ticket for payment failure"} | ConvertTo-Json'
Write-Host '  Invoke-RestMethod -Uri http://localhost:8080/orchestrate -Method Post -Body $body -ContentType "application/json"'
Write-Host ""
Write-Host "📋 View logs:" -ForegroundColor Cyan
Write-Host "  docker compose logs -f orchestrator"
Write-Host ""
Write-Host "🛑 Stop services:" -ForegroundColor Cyan
Write-Host "  docker compose down"
Write-Host ""

