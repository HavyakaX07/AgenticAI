# 🚀 Quick Start Guide - Running the POC

## Prerequisites

1. **Docker Desktop** running on Windows
2. **Minimum 8GB RAM** available for Docker
3. **10GB disk space** for images and models

---

## 🎯 Quick Start (3 Commands)

```powershell
# 1. Navigate to the project directory
cd D:\AgenticAI\AgenticRAGWithMCP\nl-api-orchestrator

# 2. Build all services
docker-compose -f docker-compose.poc.yml build

# 3. Start all services
docker-compose -f docker-compose.poc.yml up -d
```

---

## 📋 Step-by-Step Guide

### Step 1: Build the Images

This will build all custom images (orchestrator, mcp-embed, mcp-api):

```powershell
cd D:\AgenticAI\AgenticRAGWithMCP\nl-api-orchestrator

# Build with progress output
docker-compose -f docker-compose.poc.yml build

# OR build with verbose output
docker-compose -f docker-compose.poc.yml build --progress=plain
```

**Expected time**: 5-10 minutes (first time)
- Orchestrator: ~2 min
- MCP Embed: ~3-5 min (downloads embedding model)
- MCP API: ~1 min
- Ollama, OPA: Pre-built images (fast)

### Step 2: Start All Services

```powershell
# Start in detached mode (background)
docker-compose -f docker-compose.poc.yml up -d

# OR start with logs visible
docker-compose -f docker-compose.poc.yml up
```

### Step 3: Wait for Services to Initialize

```powershell
# Check status of all services
docker-compose -f docker-compose.poc.yml ps

# Watch logs
docker-compose -f docker-compose.poc.yml logs -f
```

### Step 4: Download Ollama Model (First Time Only)

The Ollama container needs to download the LLM model:

```powershell
# Pull the Llama 3.1 8B model (~4.7GB)
docker exec -it nl-api-orchestrator-ollama-1 ollama pull llama3.1:8b

# OR use a smaller model for testing (~2GB)
docker exec -it nl-api-orchestrator-ollama-1 ollama pull llama3.2:3b
```

**Note**: If using the smaller model, update the orchestrator environment:
```yaml
- MODEL_NAME=llama3.2:3b
```

### Step 5: Verify All Services Are Running

```powershell
# Health check all services
curl http://localhost:8080/health  # Orchestrator
curl http://localhost:9001/health  # MCP Embed
curl http://localhost:9000/health  # MCP API
curl http://localhost:8181/health  # OPA Policy
curl http://localhost:11434/api/tags  # Ollama (list models)
```

---

## 🧪 Test the System

### Test 1: Simple Orchestration Request

```powershell
$body = @{
    user_input = "List all tickets"
    user_id = "user123"
    user_role = "support_agent"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/orchestrate" -Method Post -Body $body -ContentType "application/json"
```

### Test 2: Embedding Search

```powershell
$body = @{
    text = "create a ticket"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:9001/embed" -Method Post -Body $body -ContentType "application/json"
```

---

## 🛠️ Common Commands

### View Logs

```powershell
# All services
docker-compose -f docker-compose.poc.yml logs -f

# Specific service
docker-compose -f docker-compose.poc.yml logs -f orchestrator
docker-compose -f docker-compose.poc.yml logs -f ollama
docker-compose -f docker-compose.poc.yml logs -f mcp-embed
```

### Stop Services

```powershell
# Stop all (preserves data)
docker-compose -f docker-compose.poc.yml stop

# Stop and remove containers (preserves volumes)
docker-compose -f docker-compose.poc.yml down

# Stop and remove everything including volumes
docker-compose -f docker-compose.poc.yml down -v
```

### Restart a Specific Service

```powershell
docker-compose -f docker-compose.poc.yml restart orchestrator
```

### Rebuild After Code Changes

```powershell
# Rebuild specific service
docker-compose -f docker-compose.poc.yml build orchestrator

# Rebuild and restart
docker-compose -f docker-compose.poc.yml up -d --build orchestrator
```

---

## 📊 Service Status

Check which services are running:

```powershell
docker-compose -f docker-compose.poc.yml ps
```

Expected output:
```
NAME                            STATUS              PORTS
nl-api-orchestrator-ollama-1    running            0.0.0.0:11434->11434/tcp
nl-api-orchestrator-orchestrator-1  running        0.0.0.0:8080->8080/tcp
nl-api-orchestrator-mcp-api-1   running            0.0.0.0:9000->9000/tcp
nl-api-orchestrator-mcp-embed-1 running            0.0.0.0:9001->9001/tcp
nl-api-orchestrator-mcp-policy-1 running           0.0.0.0:8181->8181/tcp
```

---

## 🐛 Troubleshooting

### Issue: "Dockerfile.alpine not found"

**Solution**: Use Dockerfile.fast instead:

```powershell
# Edit docker-compose.poc.yml line 101
dockerfile: Dockerfile.fast  # Change from Dockerfile.alpine
```

### Issue: Ollama model not found

**Solution**: Pull the model manually:

```powershell
docker exec -it nl-api-orchestrator-ollama-1 ollama pull llama3.1:8b
```

### Issue: Service failed to start

**Solution**: Check logs:

```powershell
docker-compose -f docker-compose.poc.yml logs <service-name>
```

### Issue: Port already in use

**Solution**: Check what's using the port:

```powershell
netstat -ano | findstr :8080
```

### Issue: Out of memory

**Solution**: Increase Docker memory in Docker Desktop settings (minimum 8GB recommended)

---

## 🔄 Complete Restart

If things go wrong, complete reset:

```powershell
# Stop everything
docker-compose -f docker-compose.poc.yml down -v

# Remove all related images
docker images | Select-String "nl-api-orchestrator" | ForEach-Object { docker rmi -f $_.ToString().Split()[2] }

# Rebuild from scratch
docker-compose -f docker-compose.poc.yml build --no-cache

# Start again
docker-compose -f docker-compose.poc.yml up -d
```

---

## 📈 Expected Resource Usage

| Service | CPU | Memory | Disk |
|---------|-----|--------|------|
| Ollama (with model) | 10-50% | 2-4GB | ~5GB |
| Orchestrator | 1-5% | 200-500MB | 500MB |
| MCP Embed | 1-5% | 500MB-1GB | 1.5GB |
| MCP API | <1% | 100-200MB | 200MB |
| OPA Policy | <1% | 50-100MB | 10MB |
| **Total** | - | **4-8GB** | **~8GB** |

---

## ✅ Success Indicators

You'll know everything is working when:

1. ✓ All 5 services show "running (healthy)" status
2. ✓ All health endpoints return 200 OK
3. ✓ Ollama has the model loaded: `ollama list` shows llama3.1:8b
4. ✓ Test orchestration request returns a response with tool selection
5. ✓ No error messages in logs

---

## 🎓 What Each Service Does

- **Orchestrator** (8080): Main brain - receives requests, selects tools, calls LLM
- **Ollama** (11434): Local LLM server - generates responses using Llama model
- **MCP Embed** (9001): Embedding service - matches user queries to capabilities
- **MCP API** (9000): Tool executor - makes actual API calls
- **OPA Policy** (8181): Security - checks if user is authorized to use tools

