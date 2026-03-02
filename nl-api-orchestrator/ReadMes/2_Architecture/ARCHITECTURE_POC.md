# 🏗️ POC Architecture - Visual Guide

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                             │
│                    "Create a ticket for login bug"               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Port 8080)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Step 1: RAG - Retrieve Capabilities                      │  │
│  │  ─────────────────────────────────────                    │  │
│  │  Query → Embed → Similarity Search → Top-K Capabilities   │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                            │ capabilities                        │
│                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Step 2: LLM Reasoning                                    │  │
│  │  ────────────────────────                                 │  │
│  │  Capabilities + Query → LLM → Tool Selection + Params     │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                            │ tool_name, payload                  │
│                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Step 3: Validate Payload                                 │  │
│  │  ───────────────────────────                              │  │
│  │  JSON Schema Validation → ✓ Valid / ✗ Invalid            │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                            │ validated_payload                   │
│                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Step 4: Policy Check                                     │  │
│  │  ───────────────────────                                  │  │
│  │  OPA Policy Engine → ✓ Allow / ✗ Deny                    │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                            │ policy_result                       │
│                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Step 5: Execute Tool via MCP                             │  │
│  │  ────────────────────────────────                         │  │
│  │  MCP Protocol → API Call → Result                         │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                            │ api_result                          │
│                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Step 6: Format Response                                  │  │
│  │  ──────────────────────────                               │  │
│  │  Result → User-Friendly Message                           │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
└────────────────────────────┼────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                      RESPONSE TO USER                            │
│  {                                                               │
│    "decision": "USE_TOOL",                                       │
│    "tool_used": "create_ticket",                                 │
│    "message": "Created ticket #123 successfully."                │
│  }                                                               │
└──────────────────────────────────────────────────────────────────┘
```

## Service Dependencies

```
                    ┌──────────────────┐
                    │  ORCHESTRATOR    │ ← Main Service (Port 8080)
                    │   (FastAPI)      │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┬──────────────┐
         │                   │                   │              │
         ▼                   ▼                   ▼              ▼
┌────────────────┐  ┌────────────────┐  ┌──────────────┐  ┌─────────┐
│  OLLAMA (LLM)  │  │  MCP-EMBED     │  │  MCP-API     │  │   OPA   │
│  Port: 11434   │  │  Port: 9001    │  │  Port: 9000  │  │ Port:   │
│                │  │                │  │              │  │  8181   │
│  • Model:      │  │  • BGE         │  │  • Create    │  │         │
│    llama3.1:8b │  │    Embeddings  │  │    Ticket    │  │ • Policy│
│  • OpenAI API  │  │  • FAISS       │  │  • List      │  │   Engine│
│  • Local       │  │    Search      │  │    Tickets   │  │ • Rego  │
│                │  │  • RAG         │  │  • HTTP      │  │   Rules │
└────────────────┘  └────────────────┘  └──────────────┘  └─────────┘
```

## Component Breakdown

### 1. Orchestrator (Core Brain)
```
Input:  Natural Language Query
Output: Structured Response

Technologies:
├── FastAPI (Web Framework)
├── Pydantic (Data Validation)
├── OpenAI SDK (LLM Client)
└── HTTPX (Async HTTP)

Responsibilities:
├── Receive user queries
├── Coordinate all services
├── Implement business logic
└── Error handling
```

### 2. Ollama (LLM Server)
```
Input:  Prompt + Context
Output: Tool Selection + Parameters

Technologies:
├── Llama 3.1 8B (Model)
├── GGUF Format (Quantized)
└── OpenAI Compatible API

Responsibilities:
├── Understand natural language
├── Select appropriate tool
├── Extract parameters
└── Generate reasoning
```

### 3. MCP-Embed (RAG Component)
```
Input:  Query Text
Output: Top-K Similar Capabilities

Technologies:
├── Sentence Transformers
├── FAISS (Vector Search)
└── BGE-small-en-v1.5 (Embedding Model)

Responsibilities:
├── Generate embeddings
├── Compute cosine similarity
├── Retrieve relevant capabilities
└── Cache embeddings
```

### 4. MCP-API (Tool Executor)
```
Input:  Tool Name + Arguments
Output: API Result

Technologies:
├── FastAPI (Server)
├── HTTPX (HTTP Client)
└── MCP Protocol

Responsibilities:
├── Implement MCP protocol
├── Execute API calls
├── Validate inputs
└── Return structured results
```

### 5. OPA (Policy Engine)
```
Input:  Policy Query
Output: Allow / Deny Decision

Technologies:
├── Open Policy Agent
└── Rego (Policy Language)

Responsibilities:
├── Enforce security policies
├── Authorization checks
├── Risk assessment
└── Audit logging
```

## Data Flow Example

### Example Query: "Create a ticket for login bug"

```
1. USER → ORCHESTRATOR
   POST /orchestrate
   {"query": "Create a ticket for login bug"}

2. ORCHESTRATOR → MCP-EMBED
   POST /embed
   {"text": "Create a ticket for login bug"}
   
   RESPONSE:
   {
     "embedding": [0.12, -0.45, 0.78, ...],
     "top_matches": [
       {
         "name": "create_ticket",
         "similarity": 0.94,
         "description": "Create a support ticket"
       }
     ]
   }

3. ORCHESTRATOR → OLLAMA
   POST /v1/chat/completions
   {
     "messages": [
       {"role": "system", "content": "You are an API orchestrator..."},
       {"role": "user", "content": "Select tool for: Create a ticket..."}
     ],
     "capabilities": [...]
   }
   
   RESPONSE:
   {
     "decision": "USE_TOOL",
     "tool_name": "create_ticket",
     "payload": {
       "title": "Login bug",
       "description": "User reported login issue",
       "priority": "medium"
     }
   }

4. ORCHESTRATOR → OPA
   POST /v1/data/policy/allow
   {
     "input": {
       "tool": "create_ticket",
       "payload": {...},
       "user": "default_user"
     }
   }
   
   RESPONSE:
   {
     "result": true,
     "reason": "User authorized for create_ticket"
   }

5. ORCHESTRATOR → MCP-API
   POST /invoke
   {
     "tool_name": "create_ticket",
     "arguments": {
       "title": "Login bug",
       "description": "User reported login issue",
       "priority": "medium"
     }
   }
   
   RESPONSE:
   {
     "status": "success",
     "ticket_id": "TICKET-123",
     "created_at": "2026-02-12T20:00:00Z"
   }

6. ORCHESTRATOR → USER
   {
     "decision": "USE_TOOL",
     "tool_used": "create_ticket",
     "api_result": {
       "ticket_id": "TICKET-123"
     },
     "message": "Created ticket TICKET-123 successfully."
   }
```

## Technology Stack Summary

```
┌─────────────────────────────────────────────────┐
│              Application Layer                   │
│  ┌─────────────┐  ┌──────────────┐             │
│  │  FastAPI    │  │  Pydantic    │             │
│  │  (REST API) │  │  (Validation)│             │
│  └─────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│               AI/ML Layer                        │
│  ┌─────────────┐  ┌──────────────┐             │
│  │ Llama 3.1   │  │ Sentence     │             │
│  │ (LLM)       │  │ Transformers │             │
│  │             │  │ (Embeddings) │             │
│  └─────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│              Data Layer                          │
│  ┌─────────────┐  ┌──────────────┐             │
│  │   FAISS     │  │  JSON Files  │             │
│  │  (Vector DB)│  │  (Config)    │             │
│  └─────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│             Security Layer                       │
│  ┌─────────────┐  ┌──────────────┐             │
│  │     OPA     │  │  JSON Schema │             │
│  │  (Policies) │  │  (Validation)│             │
│  └─────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│           Infrastructure Layer                   │
│  ┌─────────────┐  ┌──────────────┐             │
│  │   Docker    │  │  Docker      │             │
│  │             │  │  Compose     │             │
│  └─────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────┘
```

## Performance Characteristics

### Latency Breakdown (CPU Mode)
```
Total Request: ~12-15 seconds
├── RAG Retrieval:     ~200ms  ( 1.5%)
├── LLM Inference:     ~10s    (70.0%)  ← Bottleneck
├── Validation:        ~10ms   ( 0.1%)
├── Policy Check:      ~50ms   ( 0.4%)
└── Tool Execution:    ~2s     (14.0%)
    Network overhead:  ~500ms  ( 3.5%)
```

### Latency Breakdown (GPU Mode)
```
Total Request: ~4-6 seconds
├── RAG Retrieval:     ~200ms  ( 4.0%)
├── LLM Inference:     ~2s     (40.0%)  ← Much faster
├── Validation:        ~10ms   ( 0.2%)
├── Policy Check:      ~50ms   ( 1.0%)
└── Tool Execution:    ~2s     (40.0%)
    Network overhead:  ~500ms  (10.0%)
```

### Resource Usage (POC)
```
Service          CPU    Memory   Disk
─────────────────────────────────────
orchestrator     10%    200MB    500MB
ollama (CPU)     100%   2GB      4.7GB
ollama (GPU)     20%    4GB      4.7GB
mcp-embed        5%     800MB    800MB
mcp-api          2%     100MB    300MB
opa              1%     50MB     50MB
─────────────────────────────────────
Total (CPU)      ~120%  3.2GB    6.4GB
Total (GPU)      ~35%   5.2GB    6.4GB
```

## Scalability Considerations

### Current (POC)
```
Single Instance
├── Throughput: ~5 req/min (CPU), ~15 req/min (GPU)
├── Concurrent: 1-2 users
└── Suitable for: Demo, Testing, Development
```

### Production Scaling
```
Multiple Instances + Load Balancer
├── Throughput: 100+ req/min
├── Concurrent: 50+ users
├── Horizontal scaling of orchestrator
├── Separate LLM server pool
└── Vector DB for embeddings
```

---

**Note**: This is the POC architecture. Production adds monitoring layers
(OpenTelemetry, Prometheus, Grafana, Loki) not shown here.

