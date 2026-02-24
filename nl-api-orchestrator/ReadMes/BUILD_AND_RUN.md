# 🎯 POC Build & Run - Complete Guide

## ⚡ Super Quick Start (Copy & Paste)

```powershell
cd D:\AgenticAI\AgenticRAGWithMCP\nl-api-orchestrator
.\run-poc.ps1
```

---

## 📋 What Happens When You Run It

### Phase 1: Pre-flight Checks ✈️
```
✓ Docker is running
✓ Dockerfile references are correct
```

### Phase 2: Build Images 🏗️ (5-10 minutes)
```
Building orchestrator...     [█████████░] ~2 min
Building mcp-embed...        [█████████░] ~3-5 min (downloads model)
Building mcp-api...          [█████████░] ~1 min
Pulling ollama...            [█████████░] ~1 min
Pulling opa...               [█████████░] ~10 sec
```

### Phase 3: Start Services 🚀 (30 seconds)
```
Starting ollama...           ✓
Starting opa-policy...       ✓
Starting mcp-api...          ✓
Starting mcp-embed...        ✓
Starting orchestrator...     ✓
```

### Phase 4: Health Checks 🏥
```
✓ MCP API Tools is healthy
✓ MCP Embeddings is healthy
✓ OPA Policy is healthy
✓ Ollama is healthy
✓ Orchestrator is healthy
```

### Phase 5: Model Download 📥 (2-5 GB, one-time)
```
Pulling llama3.2:3b model... [█████████░] ~3 min
✓ Model downloaded successfully
```

### Phase 6: Ready! 🎉
```
========================================
POC Environment Ready!
========================================

Services:
  • Orchestrator:    http://localhost:8080
  • Ollama LLM:      http://localhost:11434
  • MCP API Tools:   http://localhost:9000
  • MCP Embeddings:  http://localhost:9001
  • OPA Policy:      http://localhost:8181
```

---

## 🧪 Test Commands

### Test 1: Simple Health Check
```powershell
curl http://localhost:8080/health
```
**Expected**: `{"status":"healthy"}`

### Test 2: Full Orchestration Request
```powershell
$body = @{
    user_input = "List all tickets"
    user_id = "user123"
    user_role = "support_agent"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/orchestrate" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

**Expected Response**:
```json
{
  "tool_selected": "list_tickets",
  "reasoning": "User wants to retrieve all support tickets",
  "result": {
    "tickets": [...]
  }
}
```

---

## 🎛️ Script Options

```powershell
# Start everything
.\run-poc.ps1 -Action start

# Skip rebuild if images exist
.\run-poc.ps1 -Action start -NoBuild

# Stop all services
.\run-poc.ps1 -Action stop

# Restart services
.\run-poc.ps1 -Action restart

# Check status and health
.\run-poc.ps1 -Action status

# View live logs
.\run-poc.ps1 -Action logs

# Clean up everything
.\run-poc.ps1 -Action clean
```

---

## 📊 Manual Docker Compose Commands

If you prefer manual control:

```powershell
# Build
docker-compose -f docker-compose.poc.yml build

# Start in background
docker-compose -f docker-compose.poc.yml up -d

# Start with visible logs
docker-compose -f docker-compose.poc.yml up

# Stop
docker-compose -f docker-compose.poc.yml stop

# Stop and remove
docker-compose -f docker-compose.poc.yml down

# View logs
docker-compose -f docker-compose.poc.yml logs -f

# Check status
docker-compose -f docker-compose.poc.yml ps

# Rebuild specific service
docker-compose -f docker-compose.poc.yml build orchestrator
docker-compose -f docker-compose.poc.yml up -d orchestrator
```

---

## 🎯 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Orchestrator | http://localhost:8080 | Main API endpoint |
| Ollama | http://localhost:11434 | LLM server |
| MCP Embed | http://localhost:9001 | Embedding generation |
| MCP API | http://localhost:9000 | Tool execution |
| OPA Policy | http://localhost:8181 | Authorization |

### API Endpoints

**Orchestrator**:
- `GET /health` - Health check
- `POST /orchestrate` - Main endpoint
- `GET /capabilities` - List available tools

**MCP Embed**:
- `GET /health` - Health check
- `POST /embed` - Generate embedding
- `POST /search` - Search capabilities

**MCP API**:
- `GET /health` - Health check
- `POST /tools/{tool_name}` - Execute tool

**Ollama**:
- `GET /api/tags` - List models
- `POST /api/generate` - Generate text

**OPA**:
- `GET /health` - Health check
- `POST /v1/data/nl_api/allow` - Check policy

---

## 🐛 Common Issues & Solutions

### Issue 1: Docker Not Running
```
ERROR: error during connect
```
**Solution**: Start Docker Desktop

### Issue 2: Port Already in Use
```
ERROR: port 8080 is already allocated
```
**Solution**: 
```powershell
# Find what's using the port
netstat -ano | findstr :8080

# Kill the process or change port in docker-compose.poc.yml
```

### Issue 3: Build Failed
```
ERROR: failed to solve
```
**Solution**:
```powershell
# Clean and rebuild
docker-compose -f docker-compose.poc.yml down
docker-compose -f docker-compose.poc.yml build --no-cache
```

### Issue 4: Service Unhealthy
```
✗ Orchestrator is not responding
```
**Solution**:
```powershell
# Check logs
docker-compose -f docker-compose.poc.yml logs orchestrator

# Restart service
docker-compose -f docker-compose.poc.yml restart orchestrator
```

### Issue 5: Out of Memory
```
ERROR: no space left on device
```
**Solution**: 
- Increase Docker memory limit in Docker Desktop settings
- Minimum 8GB RAM recommended
- Free up disk space (need ~10GB)

---

## 📦 Resource Requirements

| Component | CPU | Memory | Disk |
|-----------|-----|--------|------|
| Orchestrator | 1-5% | 200-500MB | 500MB |
| Ollama + Model | 10-50% | 2-4GB | 5GB |
| MCP Embed | 1-5% | 500MB-1GB | 1.5GB |
| MCP API | <1% | 100-200MB | 200MB |
| OPA | <1% | 50-100MB | 10MB |
| **TOTAL** | - | **4-8GB** | **~8GB** |

---

## ⏱️ Expected Timings

| Operation | First Time | Subsequent |
|-----------|------------|------------|
| Build images | 10-15 min | 1-3 min |
| Start services | 1-2 min | 30-60 sec |
| Download model | 3-5 min | 0 sec (cached) |
| Health checks | 30 sec | 10 sec |
| **TOTAL** | **15-20 min** | **1-2 min** |

---

## 📚 Documentation Files

- `QUICK_START_POC.md` - This file (quick reference)
- `RUN_POC.md` - Detailed step-by-step guide
- `POC_ARCHITECTURE.md` - Architecture overview
- `docker-compose.poc.yml` - Service definitions

---

## ✅ Success Checklist

- [ ] Docker Desktop is running
- [ ] All 5 services show "running (healthy)"
- [ ] Health endpoints return 200 OK
- [ ] Ollama model is downloaded
- [ ] Test request returns valid response
- [ ] No errors in logs

---

## 🎓 Next Steps

1. **Test with different queries**:
   - "Create a ticket with title 'Bug report'"
   - "Update ticket 123"
   - "Show me all open tickets"

2. **Check the logs**:
   ```powershell
   .\run-poc.ps1 -Action logs
   ```

3. **Explore the APIs**:
   - Visit http://localhost:8080/docs (FastAPI Swagger UI)
   - Visit http://localhost:9000/docs (MCP API docs)
   - Visit http://localhost:9001/docs (Embed API docs)

4. **Modify capabilities**:
   - Edit `orchestrator/registry/capabilities.json`
   - Restart orchestrator:
     ```powershell
     docker-compose -f docker-compose.poc.yml restart orchestrator
     ```

5. **Read the architecture**:
   - See `POC_ARCHITECTURE.md` for detailed flow diagrams

---

## 🚀 You're All Set!

Your POC environment is ready for development and testing. Happy coding! 🎉

