# =============================================================================
# Build and test optimized embed_tools Docker image
# =============================================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("fast", "minimal", "alpine")]
    [string]$Version = "fast"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building MCP Embed Tools - Optimized" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$DockerfilePath = "mcp\embed_tools\Dockerfile.$Version"
$ImageName = "mcp-embed:$Version"
$ContainerName = "test-mcp-embed-$Version"

# Check if Dockerfile exists
if (-not (Test-Path $DockerfilePath)) {
    Write-Host "Error: $DockerfilePath not found!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[1/5] Enabling Docker BuildKit for faster builds..." -ForegroundColor Yellow
$env:DOCKER_BUILDKIT = "1"

Write-Host "`n[2/5] Building Docker image..." -ForegroundColor Yellow
Write-Host "This may take 5-20 minutes depending on your connection..." -ForegroundColor Gray
$buildStart = Get-Date

docker build -t $ImageName -f $DockerfilePath mcp\embed_tools

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nBuild failed!" -ForegroundColor Red
    exit 1
}

$buildEnd = Get-Date
$buildTime = ($buildEnd - $buildStart).TotalMinutes

Write-Host "`n[3/5] Build completed in $([math]::Round($buildTime, 2)) minutes" -ForegroundColor Green

Write-Host "`n[4/5] Checking image size..." -ForegroundColor Yellow
docker images $ImageName --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

Write-Host "`n[5/5] Running quick test..." -ForegroundColor Yellow

# Stop and remove existing container if present
docker stop $ContainerName 2>$null
docker rm $ContainerName 2>$null

# Start container
Write-Host "Starting container..." -ForegroundColor Gray
docker run -d -p 9001:9001 --name $ContainerName $ImageName

# Wait for startup
Write-Host "Waiting for service to start..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Test health endpoint
Write-Host "Testing health endpoint..." -ForegroundColor Gray
$healthResponse = Invoke-WebRequest -Uri "http://localhost:9001/health" -UseBasicParsing -ErrorAction SilentlyContinue

if ($healthResponse.StatusCode -eq 200) {
    Write-Host "✓ Health check passed!" -ForegroundColor Green
} else {
    Write-Host "✗ Health check failed!" -ForegroundColor Red
}

# Test embed endpoint
Write-Host "Testing embed endpoint..." -ForegroundColor Gray
$embedBody = @{
    text = "test query"
} | ConvertTo-Json

$embedResponse = Invoke-WebRequest -Uri "http://localhost:9001/embed" -Method Post -Body $embedBody -ContentType "application/json" -UseBasicParsing -ErrorAction SilentlyContinue

if ($embedResponse.StatusCode -eq 200) {
    Write-Host "✓ Embed endpoint working!" -ForegroundColor Green
    $result = $embedResponse.Content | ConvertFrom-Json
    Write-Host "  Vector dimensions: $($result.vector.Count)" -ForegroundColor Gray
} else {
    Write-Host "✗ Embed endpoint failed!" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Build Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Image: $ImageName" -ForegroundColor White
Write-Host "Build time: $([math]::Round($buildTime, 2)) minutes" -ForegroundColor White
Write-Host "Container: $ContainerName (running on port 9001)" -ForegroundColor White
Write-Host "`nTo stop the test container:" -ForegroundColor Yellow
Write-Host "  docker stop $ContainerName" -ForegroundColor Gray
Write-Host "`nTo view logs:" -ForegroundColor Yellow
Write-Host "  docker logs $ContainerName" -ForegroundColor Gray
Write-Host "`nTo remove the container:" -ForegroundColor Yellow
Write-Host "  docker rm -f $ContainerName" -ForegroundColor Gray

