# 🎯 Quick Reference Card - POC

## 🚀 START COMMANDS

```powershell
# Method 1: Script (Recommended)
cd D:\AgenticAI\AgenticRAGWithMCP\nl-api-orchestrator
.\start-poc.ps1

# Method 2: Manual
docker compose -f docker-compose.poc.yml up -d
docker compose -f docker-compose.poc.yml exec ollama ollama pull llama3.1:8b
```

## 🧪 TEST COMMANDS

```powershell
# Health check
curl http://localhost:8080/health

# Create ticket
curl -X POST http://localhost:8080/orchestrate -H "Content-Type: application/json" -d '{\"query\":\"Create a ticket for login bug\"}'

# List tickets
curl -X POST http://localhost:8080/orchestrate -H "Content-Type: application/json" -d '{\"query\":\"Show me all tickets\"}'

# API docs
Start-Process http://localhost:8080/docs
```

## 📊 SERVICE PORTS

| Service | Port | URL |
|---------|------|-----|
| Orchestrator | 8080 | http://localhost:8080 |
| Ollama | 11434 | http://localhost:11434 |
| MCP Embed | 9001 | http://localhost:9001 |
| MCP API | 9000 | http://localhost:9000 |
| OPA | 8181 | http://localhost:8181 |

## 🔍 MONITORING COMMANDS

```powershell
# View all logs
docker compose -f docker-compose.poc.yml logs -f

# View specific service
docker compose -f docker-compose.poc.yml logs -f orchestrator
docker compose -f docker-compose.poc.yml logs -f ollama

# Check status
docker compose -f docker-compose.poc.yml ps

# Resource usage
docker stats
```

## 🔄 MANAGEMENT COMMANDS

```powershell
# Restart service
docker compose -f docker-compose.poc.yml restart orchestrator

# Stop all
docker compose -f docker-compose.poc.yml down

# Clean restart (removes volumes)
docker compose -f docker-compose.poc.yml down -v
docker compose -f docker-compose.poc.yml up --build -d

# Rebuild specific service
docker compose -f docker-compose.poc.yml up -d --build orchestrator
```

## 📁 KEY FILES

```
✅ docker-compose.poc.yml              Main config
✅ README_POC.md                       POC guide
✅ ARCHITECTURE_POC.md                 Architecture
✅ INTERVIEW_GUIDE_COMPLETE.md         Interview prep
✅ FILE_STRUCTURE_GUIDE.md             File guide
✅ FINAL_SUMMARY.md                    Summary

orchestrator/
  ✅ Dockerfile.poc                    Build config
  ✅ requirements.poc.txt              Dependencies
  ✅ src/app_poc.py                    Main app
  ✅ registry/capabilities.json        API specs
```

## 🐛 TROUBLESHOOTING

### Services won't start
```powershell
docker compose -f docker-compose.poc.yml logs
docker compose -f docker-compose.poc.yml down -v
docker compose -f docker-compose.poc.yml up --build -d
```

### Model download fails
```powershell
docker compose -f docker-compose.poc.yml exec ollama ollama pull llama3.1:8b
```

### Out of memory
```
Settings → Resources → Memory → 8GB minimum
```

### Port already in use
```powershell
# Find process using port
netstat -ano | findstr :8080

# Kill process (if needed)
taskkill /PID <PID> /F
```

## ⚡ PERFORMANCE

### Expected Latency (CPU)
- Health check: ~50ms
- RAG retrieval: ~200ms
- LLM inference: ~10-30s
- Total request: ~12-35s

### Expected Latency (GPU)
- Health check: ~50ms
- RAG retrieval: ~200ms
- LLM inference: ~2-5s
- Total request: ~3-7s

## 📖 DOCUMENTATION

| Doc | Purpose |
|-----|---------|
| README_POC.md | Getting started |
| ARCHITECTURE_POC.md | System design |
| INTERVIEW_GUIDE_COMPLETE.md | Deep dive |
| FILE_STRUCTURE_GUIDE.md | File organization |
| POC_SETUP_COMPLETE.md | Setup complete |
| FINAL_SUMMARY.md | Overview |

## 🎓 KEY CONCEPTS

### RAG (Retrieval-Augmented Generation)
- Embeds query → Searches capabilities → Returns top matches
- Model: BGE-small-en-v1.5 (384 dims)
- Search: FAISS IndexFlatL2

### LLM (Large Language Model)
- Selects tool → Extracts parameters → Returns JSON
- Model: Llama 3.1 8B (4.7GB)
- Provider: Ollama (local)

### MCP (Model Context Protocol)
- Standardized tool interface
- invoke_tool(name, args) → result
- Decouples orchestrator from APIs

### OPA (Open Policy Agent)
- Policy-as-code (Rego language)
- Authorization & validation
- Deny-by-default

## 💡 QUICK TIPS

1. **First run**: Model download takes 5-10 min
2. **Subsequent runs**: ~30 second startup
3. **GPU optional**: Works fine on CPU (slower)
4. **Logs are key**: Always check logs for errors
5. **Health endpoint**: Use to verify all services

## 🔗 USEFUL URLS

- API Docs: http://localhost:8080/docs
- Health: http://localhost:8080/health
- Ollama: http://localhost:11434
- OPA Health: http://localhost:8181/health

## 📞 SUPPORT

- Check logs: `docker compose -f docker-compose.poc.yml logs -f`
- Read docs: See README_POC.md
- GitHub issues: (if applicable)

---

**Keep this handy for quick reference! 📌**

