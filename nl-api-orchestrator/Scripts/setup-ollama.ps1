# Ollama Setup Script for Windows
# This script helps you set up Ollama after switching from vLLM

Write-Host "🚀 Setting up Ollama..." -ForegroundColor Green

# Start services
Write-Host "`n📦 Starting services..." -ForegroundColor Cyan
docker compose up -d --build

# Wait for Ollama to be ready
Write-Host "`n⏳ Waiting for Ollama to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Check if Ollama is running
$ollamaRunning = docker compose ps ollama --format json | ConvertFrom-Json
if ($ollamaRunning) {
    Write-Host "✅ Ollama is running" -ForegroundColor Green
} else {
    Write-Host "❌ Ollama is not running. Check logs with: docker compose logs ollama" -ForegroundColor Red
    exit 1
}

# Pull the default model
Write-Host "`n📥 Pulling llama3.1:8b model (this may take a few minutes)..." -ForegroundColor Cyan
docker compose exec ollama ollama pull llama3.1:8b

# List available models
Write-Host "`n📋 Available models:" -ForegroundColor Cyan
docker compose exec ollama ollama list

# Check orchestrator health
Write-Host "`n🏥 Checking orchestrator health..." -ForegroundColor Cyan
Start-Sleep -Seconds 5
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing
    Write-Host "✅ Orchestrator is healthy: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Orchestrator not ready yet. Check logs with: docker compose logs orchestrator" -ForegroundColor Yellow
}

# Show service status
Write-Host "`n📊 Service Status:" -ForegroundColor Cyan
docker compose ps

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. Test orchestration: curl -X POST http://localhost:8080/orchestrate -H 'Content-Type: application/json' -d '{`"query`":`"Create a ticket for bug fix`"}'" -ForegroundColor White
Write-Host "  2. View logs: docker compose logs -f orchestrator" -ForegroundColor White
Write-Host "  3. Access Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "  4. Access Jaeger: http://localhost:16686" -ForegroundColor White

