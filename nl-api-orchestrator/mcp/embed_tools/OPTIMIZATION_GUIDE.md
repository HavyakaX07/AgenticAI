# Docker Image Size Optimization Guide

## 📊 Image Size Comparison

| Dockerfile | Base Image | Expected Size | Build Time | Use Case |
|------------|------------|---------------|------------|----------|
| `Dockerfile.fast` | python:3.10-slim | **~1.5-2GB** | Medium (5-10 min) | **RECOMMENDED for POC** |
| `Dockerfile.minimal` | python:3.10-slim (multi-stage) | **~1.2-1.5GB** | Medium (5-10 min) | Best balance of size/compatibility |
| `Dockerfile.alpine` | python:3.10-alpine | **~800MB-1.2GB** | Slow (15-20 min) | Smallest size, may have compatibility issues |
| Original (CUDA) | pytorch/pytorch:cuda | ~4-6GB | Fast (cached layers) | GPU workloads only |

---

## 🚀 Quick Start - Use the Optimized Dockerfile

### Option 1: Use `Dockerfile.fast` (RECOMMENDED)
```powershell
# Build the optimized image
docker build -t mcp-embed:optimized -f mcp\embed_tools\Dockerfile.fast mcp\embed_tools

# Check the image size
docker images mcp-embed:optimized

# Run it
docker run -d -p 9001:9001 --name mcp-embed mcp-embed:optimized
```

### Option 2: Use `Dockerfile.minimal` (Multi-stage for smallest slim-based image)
```powershell
docker build -t mcp-embed:minimal -f mcp\embed_tools\Dockerfile.minimal mcp\embed_tools
```

### Option 3: Use `Dockerfile.alpine` (Ultra-minimal, but may have issues)
```powershell
docker build -t mcp-embed:alpine -f mcp\embed_tools\Dockerfile.alpine mcp\embed_tools
```

---

## 🔧 Key Optimizations Applied

### 1. **Base Image Switch**
- **Before**: `pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime` (4GB+)
- **After**: `python:3.10-slim` (150MB base)
- **Savings**: ~3.5GB

### 2. **CPU-Only PyTorch**
```dockerfile
# Instead of full CUDA PyTorch (~2GB)
torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu
# CPU-only version is ~150MB
```

### 3. **Multi-Stage Build** (Dockerfile.minimal)
- Build stage: Install dependencies and download models
- Runtime stage: Copy only necessary files
- Removes build tools from final image (~200-300MB savings)

### 4. **Package Cleanup** (Dockerfile.alpine)
```dockerfile
# Remove test files
find /build/packages -type d -name "tests" -exec rm -rf {} +
# Remove Python cache
find /build/packages -type f -name "*.pyc" -delete
```

### 5. **Model Pre-caching**
```dockerfile
# Download model during build (not runtime)
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('BAAI/bge-small-en-v1.5')"
```

---

## 🎯 Build Time Optimization Tips

### 1. **Layer Caching**
Order Dockerfile commands from least to most frequently changed:
```dockerfile
# 1. System packages (rarely changes)
RUN apt-get update && apt-get install ...

# 2. Python dependencies (changes occasionally)
RUN pip install ...

# 3. Model download (cached after first build)
RUN python -c "from sentence_transformers ..."

# 4. Application code (changes frequently)
COPY src/ /app/src/
```

### 2. **Use BuildKit** (Faster parallel builds)
```powershell
# Enable BuildKit
$env:DOCKER_BUILDKIT=1
docker build -t mcp-embed:optimized -f mcp\embed_tools\Dockerfile.fast mcp\embed_tools
```

### 3. **Pre-pull Base Image**
```powershell
# Pull base image first (one-time)
docker pull python:3.10-slim
```

---

## 📝 Update docker-compose.yml

Update your docker-compose to use the optimized Dockerfile:

```yaml
services:
  mcp-embed:
    build:
      context: ./mcp/embed_tools
      dockerfile: Dockerfile.fast  # Changed from Dockerfile
    image: mcp-embed:optimized
    # ... rest of config
```

Or use the pre-built image:
```yaml
services:
  mcp-embed:
    image: mcp-embed:optimized
    # ... rest of config
```

---

## 🐛 Troubleshooting

### Issue: Alpine build fails with compilation errors
**Solution**: Use `Dockerfile.minimal` or `Dockerfile.fast` instead. Alpine requires compiling many packages from source.

### Issue: Model download fails during build
**Solution**: Check internet connection. The model is ~130MB and must download during build.

### Issue: "torch.utils._pytree' has no attribute 'register_pytree_node'"
**Solution**: This is a version compatibility issue. Fixed in the optimized Dockerfiles with proper torch version.

---

## 📦 Expected Final Sizes

After building, expect these approximate sizes:

```
REPOSITORY          TAG          SIZE
mcp-embed          optimized    1.5-2GB    (Dockerfile.fast)
mcp-embed          minimal      1.2-1.5GB  (Dockerfile.minimal)
mcp-embed          alpine       800MB-1.2GB (Dockerfile.alpine)
```

The model itself (`BAAI/bge-small-en-v1.5`) is ~130MB.
The rest is Python, PyTorch (CPU), FastAPI, and dependencies.

---

## ✅ Verification

After building, verify the image works:

```powershell
# Build
docker build -t mcp-embed:optimized -f mcp\embed_tools\Dockerfile.fast mcp\embed_tools

# Run
docker run -d -p 9001:9001 --name test-embed mcp-embed:optimized

# Test health endpoint
curl http://localhost:9001/health

# Test embedding endpoint
curl -X POST http://localhost:9001/embed -H "Content-Type: application/json" -d '{"text":"test query"}'

# Clean up
docker stop test-embed
docker rm test-embed
```

---

## 🎯 Recommendation

**For POC/Development**: Use `Dockerfile.fast`
- Best compatibility
- Reasonable size (~1.5-2GB)
- Medium build time
- Well-tested base image

**For Production**: Use `Dockerfile.minimal`
- Smaller size (~1.2-1.5GB)
- Multi-stage build
- Clean separation of build/runtime

**For Extreme Size Optimization**: Use `Dockerfile.alpine`
- Smallest size (~800MB-1.2GB)
- May require additional troubleshooting
- Longer initial build time

