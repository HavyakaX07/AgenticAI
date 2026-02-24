# 🚀 POC Quick Start - 3 Steps

## Method 1: Automated Script (Recommended)

```powershell
cd D:\AgenticAI\AgenticRAGWithMCP\nl-api-orchestrator
.\run-poc.ps1
```

That's it! The script will:
- ✓ Check Docker is running
- ✓ Build all images (~5-10 min first time)
- ✓ Start all services
- ✓ Check health of each service
- ✓ Download Ollama model
- ✓ Show you how to test

---

## Method 2: Manual Commands

```powershell
cd D:\AgenticAI\AgenticRAGWithMCP\nl-api-orchestrator

# Build
docker-compose -f docker-compose.poc.yml build

# Start
docker-compose -f docker-compose.poc.yml up -d

# Download model
docker exec -it nl-api-orchestrator-ollama-1 ollama pull llama3.2:3b

# Check status
docker-compose -f docker-compose.poc.yml ps
```

---

## 🧪 Test It Works

```powershell
# Test 1: Health check
curl http://localhost:8080/health

# Test 2: Full orchestration
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

---

## 📊 Available Commands

```powershell
.\run-poc.ps1 -Action start    # Start everything
.\run-poc.ps1 -Action stop     # Stop all services
.\run-poc.ps1 -Action restart  # Restart services
.\run-poc.ps1 -Action status   # Check health
.\run-poc.ps1 -Action logs     # View logs
.\run-poc.ps1 -Action clean    # Clean up
```

---

## 🎯 What You Get

| Service | Port | Purpose |
|---------|------|---------|
| Orchestrator | 8080 | Main API - handles requests |
| Ollama | 11434 | LLM server - generates responses |
| MCP Embed | 9001 | Embeddings - matches capabilities |
| MCP API | 9000 | Tool execution - calls APIs |
| OPA Policy | 8181 | Security - checks permissions |

---

## ⚡ Expected Timeline

- **First time**: 10-15 minutes (build + model download)
- **Subsequent starts**: 30-60 seconds
- **After code changes**: 1-3 minutes (rebuild only changed service)

---

## 🐛 Troubleshooting

### Docker not running?
```powershell
# Start Docker Desktop, then try again
```

### Port already in use?
```powershell
# Check what's using it
netstat -ano | findstr :8080

# Or change ports in docker-compose.poc.yml
```

### Services won't start?
```powershell
# Check logs
.\run-poc.ps1 -Action logs

# Or rebuild from scratch
.\run-poc.ps1 -Action clean
.\run-poc.ps1 -Action start
```

---

## 📖 More Details

See `RUN_POC.md` for comprehensive documentation.

