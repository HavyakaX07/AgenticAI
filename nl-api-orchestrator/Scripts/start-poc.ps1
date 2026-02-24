# ============================================================================
# POC STARTUP SCRIPT - PowerShell
# ============================================================================
# This script starts the minimal POC version without monitoring stack
# ============================================================================

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "  Starting Agentic RAG with MCP - POC Mode" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Enable Docker BuildKit for faster builds and better caching
Write-Host "Enabling Docker BuildKit for optimized builds..." -ForegroundColor Gray
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"
Write-Host "✓ BuildKit enabled" -ForegroundColor Green
Write-Host ""

# Check if Docker is running
Write-Host "[1/5] Checking Docker..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if docker-compose is available
Write-Host "[2/5] Checking docker-compose..." -ForegroundColor Yellow
try {
    docker compose version | Out-Null
    Write-Host "✓ docker-compose is available" -ForegroundColor Green
} catch {
    Write-Host "✗ docker-compose not found. Please install Docker Compose." -ForegroundColor Red
    exit 1
}

# Stop any running containers from previous runs
Write-Host "[3/5] Cleaning up previous containers..." -ForegroundColor Yellow
docker compose -f docker-compose.poc.yml down 2>&1 | Out-Null
Write-Host "✓ Cleanup complete" -ForegroundColor Green

# Build and start services
Write-Host "[4/5] Building and starting services..." -ForegroundColor Yellow
Write-Host "    This may take a few minutes on first run..." -ForegroundColor Gray
Write-Host "    (BuildKit enabled for faster builds with layer caching)" -ForegroundColor Gray
docker compose -f docker-compose.poc.yml up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Services started successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to start services" -ForegroundColor Red
    exit 1
}

# Download Ollama model
Write-Host "[5/5] Downloading Llama 3.1 model (this may take a while)..." -ForegroundColor Yellow
Write-Host "    Model size: ~4.7GB" -ForegroundColor Gray
docker compose -f docker-compose.poc.yml exec -T ollama ollama pull llama3.1:8b

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Model downloaded successfully" -ForegroundColor Green
} else {
    Write-Host "⚠ Model download failed, but you can try again later with:" -ForegroundColor Yellow
    Write-Host "    docker compose -f docker-compose.poc.yml exec ollama ollama pull llama3.1:8b" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "  POC System Started Successfully!" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Services running:" -ForegroundColor Green
Write-Host "  • Orchestrator:  http://localhost:8080" -ForegroundColor White
Write-Host "  • Health Check:  http://localhost:8080/health" -ForegroundColor White
Write-Host "  • API Docs:      http://localhost:8080/docs" -ForegroundColor White
Write-Host "  • Ollama:        http://localhost:11434" -ForegroundColor White
Write-Host "  • MCP Embed:     http://localhost:9001" -ForegroundColor White
Write-Host "  • MCP API:       http://localhost:9000" -ForegroundColor White
Write-Host "  • OPA Policy:    http://localhost:8181" -ForegroundColor White
Write-Host ""
Write-Host "Test the system:" -ForegroundColor Yellow
Write-Host '  curl -X POST http://localhost:8080/orchestrate -H "Content-Type: application/json" -d ''{"query":"Create a ticket for login bug"}''' -ForegroundColor Gray
Write-Host ""
Write-Host "View logs:" -ForegroundColor Yellow
Write-Host "  docker compose -f docker-compose.poc.yml logs -f" -ForegroundColor Gray
Write-Host ""
Write-Host "Stop the system:" -ForegroundColor Yellow
Write-Host "  docker compose -f docker-compose.poc.yml down" -ForegroundColor Gray
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan

