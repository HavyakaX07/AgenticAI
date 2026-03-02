# POC Architecture Overview

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT                                   │
│                    (Your Application)                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTP POST /orchestrate
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (Port 8080)                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 1. Receive user request                                     │ │
│  │ 2. Generate embedding from user input                       │ │
│  │ 3. Search for matching capabilities                         │ │
│  │ 4. Check authorization policy                               │ │
│  │ 5. Build prompt for LLM                                     │ │
│  │ 6. Call LLM to generate response                            │ │
│  │ 7. Execute tool if needed                                   │ │
│  │ 8. Return result to client                                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────┬───────────┬────────────┬────────────┬───────────────────────┘
      │           │            │            │
      │           │            │            │
      ▼           ▼            ▼            ▼
┌─────────┐ ┌──────────┐ ┌─────────┐ ┌────────────┐
│ OLLAMA  │ │   MCP    │ │   MCP   │ │    OPA     │
│  LLM    │ │  EMBED   │ │   API   │ │  POLICY    │
│ :11434  │ │  :9001   │ │  :9000  │ │   :8181    │
└─────────┘ └──────────┘ └─────────┘ └────────────┘
```

## 📊 Data Flow Example: "List all tickets"

```
1. CLIENT
   POST /orchestrate
   {
     "user_input": "List all tickets",
     "user_id": "user123",
     "user_role": "support_agent"
   }
   │
   ▼
2. ORCHESTRATOR - Embed user input
   POST http://mcp-embed:9001/embed
   {"text": "List all tickets"}
   │
   ▼
3. MCP-EMBED - Generate vector
   Returns: {"vector": [0.123, 0.456, ...]}  (384 dimensions)
   │
   ▼
4. ORCHESTRATOR - Search capabilities
   Uses FAISS to find closest match
   Found: "list_tickets" capability
   │
   ▼
5. ORCHESTRATOR - Check authorization
   POST http://mcp-policy:8181/v1/data/nl_api/allow
   {
     "user_role": "support_agent",
     "tool_name": "list_tickets"
   }
   │
   ▼
6. OPA-POLICY - Evaluate policy
   Returns: {"result": true}  (Allowed!)
   │
   ▼
7. ORCHESTRATOR - Build LLM prompt
   "You are an API assistant. User wants: List all tickets
    Available tools: [list_tickets]
    Select the appropriate tool..."
   │
   ▼
8. ORCHESTRATOR - Call LLM
   POST http://ollama:11434/api/generate
   {"model": "llama3.2:3b", "prompt": "..."}
   │
   ▼
9. OLLAMA - Generate response
   Returns: {
     "tool": "list_tickets",
     "reasoning": "User wants to see all tickets"
   }
   │
   ▼
10. ORCHESTRATOR - Execute tool
    POST http://mcp-api:9000/tools/list_tickets
    {"parameters": {}}
    │
    ▼
11. MCP-API - Call external API
    GET https://api.example.com/tickets
    │
    ▼
12. MCP-API - Return results
    Returns: {"tickets": [...]}
    │
    ▼
13. ORCHESTRATOR - Send to client
    Returns: {
      "tool_used": "list_tickets",
      "result": {"tickets": [...]},
      "reasoning": "..."
    }
```

## 🔧 Component Roles

### 1. **Orchestrator** (Port 8080)
**Role**: Master coordinator
- Receives all user requests
- Coordinates between all services
- Makes final decisions
- Returns results to client

**Tech**: Python, FastAPI
**Size**: ~500MB

### 2. **Ollama** (Port 11434)
**Role**: LLM inference engine
- Runs Llama language models locally
- Generates tool selections and responses
- No external API calls needed

**Tech**: Go-based LLM server
**Size**: ~100MB + model (~2-5GB)

### 3. **MCP Embed** (Port 9001)
**Role**: Semantic search engine
- Converts text to vectors (embeddings)
- Searches for matching capabilities using FAISS
- Enables "smart" capability matching

**Tech**: Python, sentence-transformers, FAISS
**Size**: ~1.5GB
**Model**: BAAI/bge-small-en-v1.5 (130MB)

### 4. **MCP API** (Port 9000)
**Role**: Tool executor
- Executes actual API calls
- Validates API URLs (allowlist)
- Handles authentication tokens
- Implements MCP protocol

**Tech**: Python, FastAPI, httpx
**Size**: ~200MB

### 5. **OPA Policy** (Port 8181)
**Role**: Security gatekeeper
- Checks if user can use specific tools
- Enforces role-based access control (RBAC)
- Prevents unauthorized tool execution

**Tech**: Rego policy language
**Size**: ~10MB

## 🔐 Security Flow

```
User Request
    │
    ▼
Orchestrator receives request
    │
    ▼
Before tool execution:
    │
    ├─► OPA checks: Can this user use this tool?
    │   - Check user_role vs tool requirements
    │   - Policy defined in policy.rego
    │
    ├─► If allowed: Continue
    │
    └─► If denied: Return error (403 Forbidden)
```

## 📦 Data Persistence

```
Volumes:
├── ollama-data/         # Stores downloaded LLM models
│   └── models/
│       └── llama3.2:3b  (~2GB)
│
└── embed-cache/         # Caches embedding models
    └── sentence-transformers/
        └── BAAI_bge-small-en-v1.5/  (~130MB)
```

**Why volumes?**
- Prevents re-downloading models on restart
- Speeds up container restarts (seconds vs minutes)
- Survives container recreation

## 🚀 Startup Sequence

```
1. Docker Compose starts all containers in parallel
   ├── Ollama        (5 sec)
   ├── OPA Policy    (2 sec)
   ├── MCP API       (5 sec)
   ├── MCP Embed     (10-15 sec) - loads embedding model
   └── Orchestrator  (15-20 sec) - waits for dependencies
                      ↑
                      Depends on all others
```

## 🔄 Request/Response Flow

### Embedding Generation
```
User Input: "create a new ticket"
    │
    ▼
Orchestrator → MCP Embed
    │
    ▼
sentence-transformers model
    │
    ▼
Vector: [0.123, -0.456, 0.789, ...]  (384 dimensions)
    │
    ▼
FAISS index search
    │
    ▼
Top 3 matching capabilities:
1. create_ticket (score: 0.92)
2. update_ticket (score: 0.67)
3. list_tickets  (score: 0.45)
```

### Tool Execution
```
Tool Selected: "create_ticket"
Parameters: {"title": "New issue", "priority": "high"}
    │
    ▼
Orchestrator → MCP API
    │
    ▼
MCP API validates URL against allowlist
    │
    ▼
MCP API makes HTTP POST to real API
    │
    ▼
Real API returns: {"ticket_id": 123, "status": "created"}
    │
    ▼
MCP API returns to Orchestrator
    │
    ▼
Orchestrator returns to Client
```

## 🎯 Why This Architecture?

### **Separation of Concerns**
- Each service has ONE job
- Easy to test independently
- Easy to replace components

### **Scalability**
- Can scale each service independently
- CPU-heavy (Ollama) separate from IO-heavy (MCP API)
- Can add multiple MCP API workers

### **Security**
- OPA provides centralized policy enforcement
- MCP API has URL allowlist
- No direct external API access from Orchestrator

### **Observability** (removed in POC but easy to add)
- Each service has health endpoints
- Logs to stdout (Docker captures)
- Can add tracing/metrics later

### **Local-First**
- No external LLM API dependencies
- Works offline (after initial model download)
- Data privacy - nothing leaves your machine

## 📈 Performance Characteristics

| Operation | Time | Bottleneck |
|-----------|------|------------|
| Embedding generation | 50-200ms | CPU (sentence-transformers) |
| FAISS search | 1-5ms | Memory access |
| OPA policy check | <1ms | In-memory evaluation |
| LLM inference | 1-10sec | CPU/GPU (model size) |
| API tool call | 100-1000ms | Network + external API |

**Total typical request**: 2-15 seconds
- Fast path (cached): ~2-3 sec
- Slow path (LLM reasoning): ~5-15 sec

## 🔮 Future Enhancements (Not in POC)

1. **Caching**: Redis for LLM response cache
2. **Monitoring**: Prometheus + Grafana dashboards
3. **Tracing**: OpenTelemetry for request tracing
4. **API Gateway**: Traefik for load balancing
5. **Vector DB**: Qdrant/Weaviate for larger datasets
6. **GPU Support**: Faster LLM inference with CUDA

