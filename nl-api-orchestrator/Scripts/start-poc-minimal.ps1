# ============================================================================
# POC Startup Script - Starts minimal Agentic RAG system
# ============================================================================

Write-Host "🚀 Starting Agentic RAG with MCP - Minimal POC" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow
$dockerRunning = docker info 2>&1 | Select-String "Server Version"
if (-not $dockerRunning) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker is running" -ForegroundColor Green

# Navigate to project directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Check if docker-compose.poc.yml exists
if (-not (Test-Path "docker-compose.poc.yml")) {
    Write-Host "❌ docker-compose.poc.yml not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🏗️  Building and starting services..." -ForegroundColor Yellow
Write-Host "   This may take 5-10 minutes on first run (downloads images + models)" -ForegroundColor Gray
Write-Host ""

# Start services
docker-compose -f docker-compose.poc.yml up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Failed to start services. Check errors above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow

# Wait for services
$maxWait = 120  # 2 minutes
$waited = 0
$allHealthy = $false

while (-not $allHealthy -and $waited -lt $maxWait) {
    Start-Sleep -Seconds 5
    $waited += 5

    $status = docker-compose -f docker-compose.poc.yml ps --format json | ConvertFrom-Json
    $unhealthy = $status | Where-Object { $_.Health -ne "healthy" -and $_.State -eq "running" }

    if ($unhealthy.Count -eq 0) {
        $allHealthy = $true
    } else {
        Write-Host "   Still waiting... ($waited seconds)" -ForegroundColor Gray
    }
}

if (-not $allHealthy) {
    Write-Host ""
    Write-Host "⚠️  Some services are not healthy yet. Checking status..." -ForegroundColor Yellow
    docker-compose -f docker-compose.poc.yml ps
    Write-Host ""
    Write-Host "💡 This is normal on first run. Services may still be downloading models." -ForegroundColor Yellow
    Write-Host "   Run 'docker-compose -f docker-compose.poc.yml logs -f' to see progress." -ForegroundColor Yellow
} else {
    Write-Host "✅ All services are healthy!" -ForegroundColor Green
}

Write-Host ""
Write-Host "📦 Checking if Ollama model is pulled..." -ForegroundColor Yellow

$modelCheck = docker exec nl-api-orchestrator-ollama-1 ollama list 2>&1 | Select-String "llama3.1:8b"

if (-not $modelCheck) {
    Write-Host "⚠️  LLM model not found. Pulling llama3.1:8b (this will take 3-5 minutes)..." -ForegroundColor Yellow
    Write-Host ""
    docker exec nl-api-orchestrator-ollama-1 ollama pull llama3.1:8b

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Model downloaded successfully!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ Failed to download model. Try manually:" -ForegroundColor Red
        Write-Host "   docker exec nl-api-orchestrator-ollama-1 ollama pull llama3.1:8b" -ForegroundColor Gray
    }
} else {
    Write-Host "✅ Model llama3.1:8b is already available" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎉 System is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Service Status:" -ForegroundColor Cyan
docker-compose -f docker-compose.poc.yml ps

Write-Host ""
Write-Host "🔗 Available Endpoints:" -ForegroundColor Cyan
Write-Host "   Orchestrator (Main API):  http://localhost:8080" -ForegroundColor White
Write-Host "   Ollama (LLM):            http://localhost:11434" -ForegroundColor White
Write-Host "   MCP Embed (RAG):         http://localhost:9001" -ForegroundColor White
Write-Host "   MCP API Tools:           http://localhost:9000" -ForegroundColor White
Write-Host "   OPA Policy:              http://localhost:8181" -ForegroundColor White

Write-Host ""
Write-Host "🧪 Test the system:" -ForegroundColor Cyan
Write-Host "   curl -X POST http://localhost:8080/orchestrate ``" -ForegroundColor White
Write-Host "     -H 'Content-Type: application/json' ``" -ForegroundColor White
Write-Host "     -d '{""query"": ""List all tickets"", ""user"": {""id"": ""demo"", ""role"": ""support_agent""}}'" -ForegroundColor White

Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "   POC Guide:       README_POC.md" -ForegroundColor White
Write-Host "   Interview Prep:  INTERVIEW_GUIDE_RAG_MCP.md" -ForegroundColor White

Write-Host ""
Write-Host "📋 Useful commands:" -ForegroundColor Cyan
Write-Host "   View logs:    docker-compose -f docker-compose.poc.yml logs -f [service-name]" -ForegroundColor Gray
Write-Host "   Stop system:  docker-compose -f docker-compose.poc.yml down" -ForegroundColor Gray
Write-Host "   Restart:      docker-compose -f docker-compose.poc.yml restart [service-name]" -ForegroundColor Gray

Write-Host ""
Write-Host "✨ Happy Building!" -ForegroundColor Green

