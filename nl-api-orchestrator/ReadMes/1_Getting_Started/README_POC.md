# 🚀 Agentic RAG with MCP - Minimal POC

> **Purpose**: Production-ready POC demonstrating Agentic RAG with Model Context Protocol (MCP)  
> **Status**: Optimized for fast Docker builds, easy demos, and interview prep  
> **Time to run**: 5-10 minutes (first time), 30 seconds (subsequent runs)

---

## 📋 What is This?

An **Agentic Retrieval-Augmented Generation (RAG)** system that:
1. Accepts natural language queries (e.g., "List all open tickets")
2. Uses **RAG** to find relevant API capabilities via semantic search
3. Leverages **LLM reasoning** (Ollama) to decide which tool to call
4. Executes API calls through **MCP (Model Context Protocol)**
5. Enforces security policies via **OPA (Open Policy Agent)**

### Architecture
```
┌─────────────┐
│    User     │ "Show me open tickets"
└──────┬──────┘
       │ HTTP POST
       v
┌──────────────────────────────────────────────────────────┐
│            Orchestrator (Brain)                          │
│  1. RAG: Find matching tools (mcp-embed service)        │
│  2. LLM: Reason about tool choice (Ollama)              │
│  3. Policy: Check authorization (OPA)                    │
│  4. Execute: Call tool (mcp-api service)                │
└──────────────────────────────────────────────────────────┘
       │           │            │              │
       v           v            v              v
   ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────────┐
   │ Ollama │ │  MCP   │ │   MCP    │ │    OPA     │
   │  LLM   │ │ Embed  │ │ API Tools│ │  Policy    │
   │        │ │ (RAG)  │ │ (Exec)   │ │  Engine    │
   └────────┘ └────────┘ └──────────┘ └────────────┘
```

---

## 🎯 Why This Architecture?

### Components Explained

| Component | Role | Why Needed |
|-----------|------|------------|
| **Orchestrator** | Main brain - coordinates everything | Handles request flow, business logic |
| **Ollama** | Local LLM server | Reasoning engine (decides which tool to call) |
| **MCP Embed** | RAG/semantic search | Finds matching API capabilities from natural language |
| **MCP API Tools** | Tool execution | Securely executes API calls (implements MCP protocol) |
| **OPA Policy** | Security/authorization | Enforces access control policies |

### Why Ollama instead of vLLM?

| Feature | Ollama (POC) | vLLM (Production) |
|---------|--------------|-------------------|
| **Setup** | ✅ 1 command | ❌ Complex config + GPU |
| **GPU Required** | ❌ No (CPU works) | ✅ Yes (8GB+ VRAM) |
| **Speed** | 🐢 2-5 sec/query | 🚀 500ms-1s/query |
| **Model Management** | ✅ Automatic | ❌ Manual HuggingFace downloads |
| **Memory** | ✅ 4-8GB RAM | ❌ 16GB+ RAM |
| **Use Case** | POC, demos, dev | Production, high-throughput |

**Decision**: Ollama is perfect for POC - easy, fast to setup, works on any machine.

---

## 🛠️ Prerequisites

- **Docker Desktop** with Docker Compose
- **8GB+ RAM** (16GB recommended)
- **10GB disk space** (for models)
- *Optional*: NVIDIA GPU for faster inference (5-10x speedup)

---

## 🚀 Quick Start

### 1. Start Services
```powershell
cd nl-api-orchestrator
docker-compose -f docker-compose.poc.yml up -d
```

**First time**: 5-10 minutes (downloads images + models)  
**Subsequent runs**: 30 seconds (everything cached)

### 2. Pull LLM Model
```powershell
# Wait for Ollama to be ready (check docker-compose logs ollama)
docker exec -it nl-api-orchestrator-ollama-1 ollama pull llama3.1:8b
```

**Time**: 3-5 minutes (4.7GB download)  
**Alternative models**: 
- `mistral:7b` (4GB, slightly faster)
- `phi3:mini` (2GB, much faster but less capable)

### 3. Verify All Services
```powershell
# Check health
docker-compose -f docker-compose.poc.yml ps

# Should see all services "healthy":
# - orchestrator (port 8080)
# - ollama (port 11434)
# - mcp-embed (port 9001)
# - mcp-api (port 9000)
# - mcp-policy (port 8181)
```

### 4. Test the System
```powershell
# Simple test
curl -X POST http://localhost:8080/orchestrate `
  -H "Content-Type: application/json" `
  -d '{"query": "List all tickets", "user": {"id": "demo", "role": "support_agent"}}'
```

**Expected flow**:
1. Orchestrator receives query
2. MCP Embed finds "list_tickets" capability via RAG
3. Ollama reasons: "Use list_tickets tool"
4. OPA checks: "support_agent can call list_tickets" ✅
5. MCP API executes: Calls external API
6. Response returned in natural language

---

## 📚 Testing Scenarios

### Scenario 1: List Tickets (Success)
```powershell
curl -X POST http://localhost:8080/orchestrate `
  -H "Content-Type: application/json" `
  -d '{
    "query": "Show me all open tickets",
    "user": {"id": "user123", "role": "support_agent"}
  }'
```

**Expected**: Returns list of tickets ✅

### Scenario 2: Create Ticket (Success)
```powershell
curl -X POST http://localhost:8080/orchestrate `
  -H "Content-Type: application/json" `
  -d '{
    "query": "Create a ticket for bug in login page",
    "user": {"id": "user123", "role": "support_agent"}
  }'
```

**Expected**: Creates ticket and returns confirmation ✅

### Scenario 3: Unauthorized Access (Denied)
```powershell
curl -X POST http://localhost:8080/orchestrate `
  -H "Content-Type: application/json" `
  -d '{
    "query": "List all tickets",
    "user": {"id": "guest", "role": "guest"}
  }'
```

**Expected**: OPA denies access ❌ (guest role not allowed)

---

## 🐛 Troubleshooting

### Issue: "Service orchestrator depends on undefined service vllm"
**Solution**: You're using the wrong docker-compose file.
```powershell
# ❌ Wrong
docker-compose up

# ✅ Correct
docker-compose -f docker-compose.poc.yml up -d
```

### Issue: Ollama not responding / model not found
**Solution**: Pull the model first
```powershell
docker exec -it nl-api-orchestrator-ollama-1 ollama pull llama3.1:8b
```

### Issue: "Embedding model download failed"
**Solution**: Check internet connection. The mcp-embed service downloads the model on first startup (300MB).
```powershell
# Check logs
docker-compose -f docker-compose.poc.yml logs mcp-embed

# Should see: "Downloading model BAAI/bge-small-en-v1.5..."
```

### Issue: Services unhealthy
**Solution**: Check logs for errors
```powershell
docker-compose -f docker-compose.poc.yml logs --tail=50 <service-name>

# Common issues:
# - orchestrator: Missing env vars (check .env file)
# - mcp-embed: Model download failed (restart: docker-compose restart mcp-embed)
# - ollama: Model not pulled (see above)
```

### Issue: Slow responses (5+ seconds)
**Solution**: 
1. **Expected on CPU**: Ollama on CPU takes 2-5 seconds per query
2. **Enable GPU**: Uncomment GPU section in docker-compose.poc.yml (requires NVIDIA GPU + drivers)
3. **Use smaller model**: `ollama pull phi3:mini` (2x faster)

---

## 📊 Monitoring (Optional)

POC has monitoring **disabled** by default (ENABLE_TRACING=false, ENABLE_METRICS=false).

To enable for production:
```yaml
# docker-compose.poc.yml
environment:
  - ENABLE_TRACING=true
  - ENABLE_METRICS=true
```

Then access:
- **Jaeger (traces)**: http://localhost:16686
- **Prometheus (metrics)**: http://localhost:9090
- **Grafana (dashboards)**: http://localhost:3000

*Note*: Adds ~1GB RAM overhead + slower startup.

---

## 🎓 Interview Preparation

### Key Points to Explain

1. **RAG (Retrieval-Augmented Generation)**
   - Converts text to vectors (embeddings)
   - Finds similar capabilities via cosine similarity
   - More dynamic than fine-tuning (no model retraining)

2. **MCP (Model Context Protocol)**
   - Standardized way for LLMs to call tools
   - Self-describing tools (name, description, input schema)
   - Security built-in (allowlists, validation)

3. **Orchestration Pattern**
   - Single entry point (orchestrator)
   - Microservices for scalability
   - Async/await for concurrency (handles 100+ req/sec)

4. **Security Layers**
   - Input validation (user input sanitization)
   - OPA policies (role-based access control)
   - Allowlist enforcement (only trusted APIs)
   - Audit logging (every action traceable)

### Demo Script for Interviews

1. **Show architecture diagram** (from this README)
2. **Start services**: `docker-compose -f docker-compose.poc.yml up -d`
3. **Explain each service** while they start:
   - "Orchestrator is the main brain..."
   - "Ollama runs the LLM locally..."
   - "MCP Embed handles semantic search..."
4. **Run test query**: Show curl command
5. **Explain request flow**: 
   - "User query goes to orchestrator..."
   - "RAG finds matching tools..."
   - "LLM decides which to call..."
   - "OPA checks authorization..."
   - "MCP executes the API call..."
6. **Show logs**: `docker-compose logs -f orchestrator`
7. **Demonstrate security**: Try unauthorized access (guest role)

### Common Interview Questions

**Q: Why microservices instead of monolith?**  
A: Independent scaling, fault isolation, technology flexibility (e.g., swap Ollama for vLLM without touching other services).

**Q: How do you handle LLM hallucinations?**  
A: RAG grounds responses in retrieved facts, structured output validation, confidence thresholds (only execute if RAG score > 0.7).

**Q: Why async/await?**  
A: LLM calls are I/O-bound (waiting 2-5 seconds). Async allows handling 100+ concurrent requests on single thread vs max ~1k with threads.

**Q: How would you scale this to production?**  
A: Horizontal scaling (multiple orchestrator replicas), caching (Redis for embeddings/LLM responses), switch to vLLM, use PostgreSQL + pgvector for capabilities.

**Q: What are security risks?**  
A: Prompt injection (user tricks LLM), data leakage (LLM exposes sensitive data), API abuse (excessive calls). Mitigations: OPA policies, input validation, rate limiting, allowlists.

---

## 📁 Project Structure

```
nl-api-orchestrator/
├── docker-compose.poc.yml          # 👈 Minimal POC config (use this!)
├── docker-compose.yml              # Full production config (monitoring, etc)
│
├── orchestrator/                   # Main orchestrator service
│   ├── Dockerfile                  # Standard build
│   ├── requirements.txt            # Python dependencies
│   ├── src/
│   │   ├── app.py                  # Main FastAPI app
│   │   ├── mcp_client.py           # LLM communication (Ollama/vLLM)
│   │   ├── retriever.py            # RAG capability matching
│   │   ├── tool_router.py          # Tool execution routing
│   │   ├── opa_client.py           # Policy enforcement
│   │   └── prompts.py              # LLM prompts
│   └── registry/
│       └── capabilities.json       # API capability definitions
│
├── mcp/
│   ├── embed_tools/                # RAG embedding service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/
│   │       └── server.py           # FastAPI app (embedding + FAISS)
│   │
│   ├── api_tools/                  # MCP tool execution
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/
│   │       ├── server.py           # MCP protocol implementation
│   │       └── tools/
│   │           ├── list_tickets.py
│   │           └── create_ticket.py
│   │
│   └── policy/                     # OPA policies
│       └── policy.rego             # Authorization rules
│
├── INTERVIEW_GUIDE_RAG_MCP.md      # 👈 Deep dive for interviews
└── README_POC.md                   # 👈 You are here!
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file in `nl-api-orchestrator/`:

```bash
# LLM Configuration
LLM_PROVIDER=ollama
LLM_BASE_URL=http://ollama:11434
MODEL_NAME=llama3.1:8b

# Service URLs (Docker network)
EMBED_SERVER_URL=http://mcp-embed:9001
API_TOOLS_URL=http://mcp-api:9000
OPA_URL=http://mcp-policy:8181

# Security
API_TOKEN=your-api-token-here
ALLOWLIST_PREFIXES=https://api.example.com/,https://jsonplaceholder.typicode.com/

# Monitoring (disable for POC)
ENABLE_TRACING=false
ENABLE_METRICS=false
LOG_LEVEL=INFO
```

---

## 🚀 Next Steps

### After POC Works

1. **Extend capabilities**: Add more tools in `mcp/api_tools/src/tools/`
2. **Production LLM**: Switch to vLLM (uncomment in docker-compose.yml)
3. **Database**: Move capabilities to PostgreSQL + pgvector
4. **Caching**: Add Redis for embeddings/LLM responses
5. **Monitoring**: Enable tracing/metrics (ENABLE_TRACING=true)
6. **Auth**: Add JWT authentication for API endpoints
7. **Rate limiting**: Add rate limiter to orchestrator

### Learn More

- **MCP Protocol**: https://modelcontextprotocol.io
- **Ollama**: https://ollama.ai
- **FAISS**: https://github.com/facebookresearch/faiss
- **OPA**: https://www.openpolicyagent.org
- **Interview Guide**: See `INTERVIEW_GUIDE_RAG_MCP.md`

---

## 📝 License

MIT License - See LICENSE file

---

## 🤝 Contributing

PRs welcome! See CONTRIBUTING.md

---

## ❓ Need Help?

1. Check logs: `docker-compose -f docker-compose.poc.yml logs <service>`
2. Verify health: `docker-compose -f docker-compose.poc.yml ps`
3. Restart service: `docker-compose -f docker-compose.poc.yml restart <service>`
4. Full rebuild: `docker-compose -f docker-compose.poc.yml up --build -d`

---

**Happy Building! 🎉**

For interview prep, read `INTERVIEW_GUIDE_RAG_MCP.md` - it covers every detail you need!

