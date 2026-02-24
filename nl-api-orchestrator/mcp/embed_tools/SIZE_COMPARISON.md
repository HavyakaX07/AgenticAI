# Quick Docker Image Size Comparison

## Test Results

Run this to compare all three optimized versions:

```powershell
# Build all three versions
docker build -t mcp-embed:fast -f mcp\embed_tools\Dockerfile.fast mcp\embed_tools
docker build -t mcp-embed:minimal -f mcp\embed_tools\Dockerfile.minimal mcp\embed_tools
docker build -t mcp-embed:alpine -f mcp\embed_tools\Dockerfile.alpine mcp\embed_tools

# Compare sizes
docker images mcp-embed --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
```

## Expected Output

```
REPOSITORY    TAG       SIZE        CREATED
mcp-embed     fast      1.5-2GB     [timestamp]
mcp-embed     minimal   1.2-1.5GB   [timestamp]
mcp-embed     alpine    800MB-1GB   [timestamp]
```

## Quick Test Script

Save this as `test-image.ps1`:

```powershell
param([string]$Tag = "fast")

$ImageName = "mcp-embed:$Tag"
$Port = 9001

Write-Host "Testing $ImageName..." -ForegroundColor Cyan

# Run container
docker run -d -p ${Port}:9001 --name test-embed-$Tag $ImageName

Start-Sleep -Seconds 5

# Test health
$health = Invoke-WebRequest -Uri "http://localhost:$Port/health" -UseBasicParsing
Write-Host "Health: $($health.StatusCode)" -ForegroundColor Green

# Test embed
$body = '{"text":"test"}' | ConvertTo-Json
$embed = Invoke-WebRequest -Uri "http://localhost:$Port/embed" -Method Post -Body $body -ContentType "application/json" -UseBasicParsing
Write-Host "Embed: $($embed.StatusCode)" -ForegroundColor Green

# Cleanup
docker stop test-embed-$Tag
docker rm test-embed-$Tag
```

## Size Breakdown

### What Takes Up Space?

1. **Base Image**: 
   - `python:3.10-slim` = ~150MB
   - `python:3.10-alpine` = ~50MB

2. **PyTorch CPU**: ~150-200MB

3. **SentenceTransformers + Dependencies**: ~300-400MB

4. **FAISS + NumPy**: ~100-150MB

5. **FastAPI + Uvicorn**: ~50MB

6. **Embedding Model (`BAAI/bge-small-en-v1.5`)**: ~130MB

7. **Other Dependencies**: ~200-300MB

**Total**: ~1.2-1.5GB (optimized) vs 4-6GB (CUDA version)

## Key Savings

| Optimization | Size Saved |
|-------------|------------|
| Use slim/alpine base instead of PyTorch CUDA | ~2-3GB |
| CPU-only PyTorch | ~1-2GB |
| Remove test files and caches | ~200-500MB |
| Multi-stage build | ~200-300MB |

## Build Time Comparison

| Version | First Build | Cached Build |
|---------|-------------|--------------|
| fast | 5-8 min | 30-60 sec |
| minimal | 5-10 min | 30-60 sec |
| alpine | 15-25 min | 1-2 min |

**Note**: Alpine is slower because it compiles many packages from source.

## Recommendation

✅ **Use `Dockerfile.fast` for POC work**
- Good balance of size, speed, and compatibility
- Well-tested base image
- ~1.5-2GB final size

