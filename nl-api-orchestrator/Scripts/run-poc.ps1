# =============================================================================
# POC Build & Run Script - One-command setup
# =============================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("start", "stop", "restart", "status", "logs", "clean")]
    [string]$Action = "start",

    [Parameter(Mandatory=$false)]
    [switch]$NoBuild
)

$ComposeFile = "docker-compose.poc.yml"
$ProjectDir = "D:\AgenticAI\AgenticRAGWithMCP\nl-api-orchestrator"

# Change to project directory
Set-Location $ProjectDir

function Write-Header {
    param([string]$Text)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Text)
    Write-Host "► $Text" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor Green
}

function Write-Error {
    param([string]$Text)
    Write-Host "✗ $Text" -ForegroundColor Red
}

function Test-Service {
    param([string]$Url, [string]$Name)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Success "$Name is healthy (${Url})"
        return $true
    }
    catch {
        Write-Error "$Name is not responding (${Url})"
        return $false
    }
}

switch ($Action) {
    "start" {
        Write-Header "Starting POC Environment"

        # Step 1: Check Docker
        Write-Step "Checking Docker..."
        try {
            docker info | Out-Null
            Write-Success "Docker is running"
        }
        catch {
            Write-Error "Docker is not running! Please start Docker Desktop."
            exit 1
        }

        # Step 2: Fix Dockerfile reference if needed
        Write-Step "Checking Dockerfile references..."
        $composeContent = Get-Content $ComposeFile -Raw
        if ($composeContent -match "Dockerfile\.alpine") {
            Write-Host "  Dockerfile.alpine found in compose file" -ForegroundColor Gray
            if (-not (Test-Path "mcp\embed_tools\Dockerfile.alpine")) {
                Write-Host "  Dockerfile.alpine not found, checking for alternatives..." -ForegroundColor Yellow
                if (Test-Path "mcp\embed_tools\Dockerfile.fast") {
                    Write-Host "  Using Dockerfile.fast instead" -ForegroundColor Yellow
                    $composeContent = $composeContent -replace "Dockerfile\.alpine", "Dockerfile.fast"
                    Set-Content $ComposeFile $composeContent
                    Write-Success "Updated to use Dockerfile.fast"
                }
            }
        }

        # Step 3: Build images
        if (-not $NoBuild) {
            Write-Step "Building Docker images (this may take 5-10 minutes first time)..."
            docker-compose -f $ComposeFile build
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Build failed!"
                exit 1
            }
            Write-Success "Build completed"
        }

        # Step 4: Start services
        Write-Step "Starting services..."
        docker-compose -f $ComposeFile up -d
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to start services!"
            exit 1
        }
        Write-Success "Services started"

        # Step 5: Wait for services
        Write-Step "Waiting for services to initialize (30 seconds)..."
        Start-Sleep -Seconds 30

        # Step 6: Check health
        Write-Step "Checking service health..."
        $allHealthy = $true

        # Check each service
        $allHealthy = $allHealthy -and (Test-Service "http://localhost:9000/health" "MCP API Tools")
        $allHealthy = $allHealthy -and (Test-Service "http://localhost:9001/health" "MCP Embeddings")
        $allHealthy = $allHealthy -and (Test-Service "http://localhost:8181/health" "OPA Policy")
        $allHealthy = $allHealthy -and (Test-Service "http://localhost:11434/api/tags" "Ollama")
        $allHealthy = $allHealthy -and (Test-Service "http://localhost:8080/health" "Orchestrator")

        # Step 7: Check Ollama model
        Write-Step "Checking Ollama model..."
        $ollamaContainer = docker-compose -f $ComposeFile ps -q ollama
        $models = docker exec $ollamaContainer ollama list 2>$null

        if ($models -match "llama3") {
            Write-Success "Ollama model already installed"
        }
        else {
            Write-Host "  No Llama model found. Pulling llama3.2:3b (smaller/faster)..." -ForegroundColor Yellow
            Write-Host "  This will download ~2GB. Press Ctrl+C to skip if you prefer." -ForegroundColor Gray
            docker exec $ollamaContainer ollama pull llama3.2:3b
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Model downloaded successfully"
            }
            else {
                Write-Host "  Note: You may need to manually pull a model later:" -ForegroundColor Yellow
                Write-Host "  docker exec -it nl-api-orchestrator-ollama-1 ollama pull llama3.2:3b" -ForegroundColor Gray
            }
        }

        # Step 8: Summary
        Write-Header "POC Environment Ready!"

        Write-Host "Services:" -ForegroundColor White
        Write-Host "  • Orchestrator:    http://localhost:8080" -ForegroundColor Gray
        Write-Host "  • Ollama LLM:      http://localhost:11434" -ForegroundColor Gray
        Write-Host "  • MCP API Tools:   http://localhost:9000" -ForegroundColor Gray
        Write-Host "  • MCP Embeddings:  http://localhost:9001" -ForegroundColor Gray
        Write-Host "  • OPA Policy:      http://localhost:8181" -ForegroundColor Gray

        Write-Host "`nQuick Test:" -ForegroundColor Yellow
        Write-Host @'
$body = @{
    user_input = "List all tickets"
    user_id = "user123"
    user_role = "support_agent"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/orchestrate" -Method Post -Body $body -ContentType "application/json"
'@ -ForegroundColor Gray

        Write-Host "`nView logs:" -ForegroundColor Yellow
        Write-Host "  .\run-poc.ps1 -Action logs" -ForegroundColor Gray

        Write-Host "`nStop services:" -ForegroundColor Yellow
        Write-Host "  .\run-poc.ps1 -Action stop" -ForegroundColor Gray
    }

    "stop" {
        Write-Header "Stopping POC Environment"
        docker-compose -f $ComposeFile stop
        Write-Success "All services stopped"
    }

    "restart" {
        Write-Header "Restarting POC Environment"
        docker-compose -f $ComposeFile restart
        Write-Success "All services restarted"
        Start-Sleep -Seconds 10

        Write-Step "Checking service health..."
        Test-Service "http://localhost:8080/health" "Orchestrator"
        Test-Service "http://localhost:9001/health" "MCP Embeddings"
    }

    "status" {
        Write-Header "POC Service Status"
        docker-compose -f $ComposeFile ps

        Write-Host "`nHealth Checks:" -ForegroundColor Yellow
        Test-Service "http://localhost:8080/health" "Orchestrator"
        Test-Service "http://localhost:9000/health" "MCP API Tools"
        Test-Service "http://localhost:9001/health" "MCP Embeddings"
        Test-Service "http://localhost:8181/health" "OPA Policy"
        Test-Service "http://localhost:11434/api/tags" "Ollama"
    }

    "logs" {
        Write-Header "POC Logs (Ctrl+C to exit)"
        docker-compose -f $ComposeFile logs -f --tail=50
    }

    "clean" {
        Write-Header "Cleaning POC Environment"
        Write-Host "This will remove all containers and images (but keep downloaded models)" -ForegroundColor Yellow
        $confirm = Read-Host "Continue? (y/n)"

        if ($confirm -eq "y") {
            Write-Step "Stopping and removing containers..."
            docker-compose -f $ComposeFile down

            Write-Step "Removing images..."
            docker images | Select-String "nl-api-orchestrator" | ForEach-Object {
                $imageId = ($_ -split "\s+")[2]
                docker rmi -f $imageId 2>$null
            }

            Write-Success "Cleanup complete"
            Write-Host "Note: Ollama models and embedding cache volumes were preserved" -ForegroundColor Gray
            Write-Host "To remove volumes too, run: docker-compose -f $ComposeFile down -v" -ForegroundColor Gray
        }
        else {
            Write-Host "Cancelled" -ForegroundColor Gray
        }
    }
}

