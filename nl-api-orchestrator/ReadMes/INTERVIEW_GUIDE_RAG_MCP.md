# Complete Interview Guide: Agentic RAG with MCP Internals

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Core Components Deep Dive](#core-components-deep-dive)
3. [MCP Protocol Internals](#mcp-protocol-internals)
4. [RAG Implementation Details](#rag-implementation-details)
5. [LLM Integration (Ollama vs vLLM)](#llm-integration-ollama-vs-vllm)
6. [Security & Policy Enforcement](#security--policy-enforcement)
7. [Request Flow & Orchestration](#request-flow--orchestration)
8. [Common Interview Questions](#common-interview-questions)

---

## System Architecture Overview

### What is Agentic RAG?
**Agentic RAG** combines:
- **Retrieval-Augmented Generation (RAG)**: Enhances LLM responses with external knowledge
- **Agentic behavior**: LLM can make decisions and execute actions (API calls, data retrieval)

### High-Level Architecture
```
User Request → Orchestrator → [LLM Decision] → Tool Selection (RAG) → Tool Execution → Response
                    ↓              ↓                    ↓                    ↓
                Policy Check   Capability Match   MCP Protocol         API Call
```

### Why This Architecture?
1. **Separation of Concerns**: Each component has a single responsibility
2. **Scalability**: Services can scale independently
3. **Security**: Policy enforcement at multiple layers
4. **Modularity**: Easy to swap LLM providers (Ollama/vLLM/OpenAI)

---

## Core Components Deep Dive

### 1. Orchestrator (Main Brain)
**File**: `orchestrator/src/app.py` or `app_poc.py`

**Responsibilities**:
- Accept natural language requests
- Invoke LLM to interpret user intent
- Match capabilities using RAG (semantic search)
- Route to appropriate MCP tool
- Aggregate and return responses

**Key Implementation Details**:

#### a) LLM Client (`mcp_client.py`)
```python
class MCPClient:
    """Manages LLM communication - works with Ollama or vLLM"""
    
    def __init__(self, base_url: str, model_name: str):
        # Ollama: http://ollama:11434
        # vLLM: http://vllm:8000/v1
        self.base_url = base_url
        self.model = model_name
    
    async def chat_completion(self, messages: List[Dict]) -> str:
        """
        Sends conversation history to LLM and gets response
        
        Why async? 
        - LLM calls take 1-5 seconds
        - Async allows other requests to be processed meanwhile
        """
        # For Ollama: POST /api/chat
        # For vLLM: POST /v1/chat/completions (OpenAI compatible)
```

**Interview Question**: *Why use async/await?*
- **Answer**: LLM inference is I/O-bound (waiting for response). Async allows handling multiple concurrent requests without blocking threads. FastAPI handles async natively with event loops.

#### b) Capability Retriever (`retriever.py`)
```python
class CapabilityRetriever:
    """RAG component - finds matching API capabilities"""
    
    def __init__(self, embed_service_url: str):
        self.embed_url = embed_service_url  # http://mcp-embed:9001
    
    async def retrieve(self, user_query: str, top_k: int = 3):
        """
        1. Send user query to embed service
        2. Embed service generates vector embedding
        3. FAISS finds nearest neighbor capabilities
        4. Returns top-k most relevant API tools
        
        Example:
        Query: "List all open tickets"
        Returns: [
            {name: "list_tickets", description: "...", score: 0.92},
            {name: "get_ticket", description: "...", score: 0.76}
        ]
        """
```

**Interview Question**: *Why separate embedding service?*
- **Answer**: 
  1. **Resource isolation**: Embedding models are memory-intensive (500MB-2GB)
  2. **Reusability**: Multiple services can use same embedding endpoint
  3. **Scalability**: Can scale embeddings independently from orchestrator

#### c) Tool Router (`tool_router.py`)
```python
class ToolRouter:
    """Routes LLM decisions to appropriate MCP tool"""
    
    async def execute(self, tool_name: str, parameters: dict):
        """
        1. Validates tool exists and is allowed (OPA policy)
        2. Calls MCP API Tools service
        3. Returns result to orchestrator
        """
        # Step 1: Policy check
        policy_ok = await self.opa_client.check_policy(tool_name, user_context)
        
        # Step 2: Execute via MCP
        result = await self.mcp_api_client.call_tool(tool_name, parameters)
        
        return result
```

---

### 2. MCP Embedding Service (RAG Engine)
**File**: `mcp/embed_tools/src/server.py`

**What is it?**
Converts text (API capabilities, user queries) into high-dimensional vectors (embeddings) for semantic similarity search.

**Key Components**:

#### a) Sentence Transformer Model
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-small-en-v1.5')
# BGE = Beijing Academy of Artificial Intelligence
# Why this model?
# - Size: 33MB (small, fast)
# - Quality: 0.85+ accuracy on semantic similarity benchmarks
# - Speed: ~100 queries/second on CPU
```

**Interview Question**: *What is an embedding?*
- **Answer**: A numerical representation of text in a high-dimensional space (384 dimensions for this model). Similar texts have similar embeddings (measured by cosine similarity).

Example:
```
"list tickets" → [0.12, -0.45, 0.78, ..., 0.34]  (384 numbers)
"show all issues" → [0.15, -0.42, 0.81, ..., 0.31]  (very similar!)
"delete user" → [-0.82, 0.61, -0.23, ..., 0.91]  (different!)
```

#### b) FAISS Index
```python
import faiss

# Create index for fast similarity search
dimension = 384  # BGE model output dimension
index = faiss.IndexFlatIP(dimension)  # IP = Inner Product (cosine similarity)

# Index capabilities once at startup
capability_texts = [
    "list_tickets: Retrieves all support tickets",
    "create_ticket: Creates a new support ticket",
    ...
]
embeddings = model.encode(capability_texts)
index.add(embeddings)

# Search
query_embedding = model.encode("show me all tickets")
scores, indices = index.search(query_embedding, k=3)
# Returns: [list_tickets (0.95), get_ticket (0.72), ...]
```

**Interview Question**: *Why FAISS instead of simple loops?*
- **Answer**: 
  - FAISS (Facebook AI Similarity Search) uses optimized C++ algorithms
  - For 100 capabilities: O(1) vs O(100) comparison
  - Supports billions of vectors with approximate search (IVF, HNSW)

#### c) Endpoints
```python
@app.post("/embed")
async def embed_text(request: EmbedRequest):
    """Generate embedding vector for text"""
    embedding = model.encode(request.text)
    return {"embedding": embedding.tolist()}

@app.post("/search")
async def search_capabilities(request: SearchRequest):
    """Find similar capabilities using RAG"""
    # 1. Embed query
    query_emb = model.encode(request.query)
    
    # 2. Search FAISS index
    scores, indices = index.search(query_emb, k=request.top_k)
    
    # 3. Return ranked capabilities
    results = [
        {
            "capability": capabilities[idx],
            "score": float(scores[0][i])
        }
        for i, idx in enumerate(indices[0])
    ]
    return {"results": results}
```

---

### 3. MCP API Tools Service (Tool Execution)
**File**: `mcp/api_tools/src/server.py`

**What is MCP?**
**Model Context Protocol** - A standardized way for LLMs to interact with external tools.

**Why MCP?**
- **Standard interface**: LLM providers (Anthropic, OpenAI) support it natively
- **Security**: Built-in authorization and validation
- **Discoverability**: Tools self-describe their capabilities

#### MCP Protocol Structure
```json
{
  "tool": {
    "name": "list_tickets",
    "description": "Retrieves all support tickets with optional filters",
    "inputSchema": {
      "type": "object",
      "properties": {
        "status": {"type": "string", "enum": ["open", "closed", "pending"]},
        "limit": {"type": "integer", "default": 10}
      }
    }
  }
}
```

#### Implementation
```python
from typing import Dict, List
import httpx

class MCPToolExecutor:
    """Executes actual API calls following MCP protocol"""
    
    def __init__(self, allowlist: List[str]):
        self.allowlist = allowlist  # Allowed API domains
        self.tools = self._register_tools()
    
    def _register_tools(self) -> Dict:
        """Register available tools at startup"""
        return {
            "list_tickets": {
                "name": "list_tickets",
                "handler": self.list_tickets_handler,
                "endpoint": "https://api.example.com/tickets",
                "method": "GET"
            },
            "create_ticket": {
                "name": "create_ticket",
                "handler": self.create_ticket_handler,
                "endpoint": "https://api.example.com/tickets",
                "method": "POST"
            }
        }
    
    async def execute(self, tool_name: str, params: dict):
        """Execute tool with security checks"""
        # 1. Validate tool exists
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        
        # 2. Validate endpoint against allowlist
        if not self._is_allowed(tool['endpoint']):
            raise SecurityError(f"Endpoint not in allowlist")
        
        # 3. Execute handler
        result = await tool['handler'](params)
        
        return result
    
    async def list_tickets_handler(self, params: dict):
        """Actual implementation of ticket listing"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.example.com/tickets",
                params=params,
                headers={"Authorization": f"Bearer {self.api_token}"}
            )
            return response.json()
```

**Interview Question**: *Why not let LLM make HTTP calls directly?*
- **Answer**:
  1. **Security**: LLM could be prompt-injected to call malicious APIs
  2. **Rate limiting**: Centralized control over API usage
  3. **Credential management**: Keeps API keys secure (not exposed to LLM)
  4. **Auditing**: All API calls are logged and traceable

---

### 4. OPA Policy Engine (Security)
**File**: `mcp/policy/policy.rego`

**What is OPA?**
Open Policy Agent - A policy engine that enforces rules using Rego language.

**Why OPA?**
- **Declarative**: Policies are data, not code
- **Fast**: Policies evaluated in microseconds
- **Separation**: Security logic separated from business logic

#### Policy Example
```rego
package nl_api.authz

# Default deny
default allow = false

# Allow tool execution if user has required role
allow {
    input.tool == "list_tickets"
    input.user.role == "support_agent"
}

allow {
    input.tool == "create_ticket"
    input.user.role in ["support_agent", "admin"]
}

# Block destructive operations for guests
deny {
    input.tool in ["delete_ticket", "delete_user"]
    input.user.role == "guest"
}
```

#### Integration
```python
class OPAClient:
    """Checks policies before allowing tool execution"""
    
    async def check_policy(self, tool_name: str, user_context: dict) -> bool:
        """
        POST http://mcp-policy:8181/v1/data/nl_api/authz/allow
        Body: {
            "input": {
                "tool": "list_tickets",
                "user": {"role": "support_agent", "id": "user123"}
            }
        }
        Response: {"result": true}
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.opa_url}/v1/data/nl_api/authz/allow",
                json={"input": {"tool": tool_name, "user": user_context}}
            )
            return response.json()["result"]
```

---

## LLM Integration (Ollama vs vLLM)

### Ollama
**What**: Local LLM runtime, similar to Docker for models

**Pros**:
- Easy setup: `ollama pull llama3.1:8b`
- Automatic model management
- Low memory mode (quantization)
- Multi-model support

**Cons**:
- Slower than vLLM (no optimizations like PagedAttention)
- CPU-friendly but not production-optimized

**API Example**:
```bash
POST http://ollama:11434/api/chat
{
  "model": "llama3.1:8b",
  "messages": [
    {"role": "user", "content": "List all tickets"}
  ]
}
```

### vLLM
**What**: High-performance LLM inference engine

**Pros**:
- **Fast**: PagedAttention algorithm (2-4x faster than Ollama)
- **Efficient**: Dynamic batching, tensor parallelism
- **OpenAI compatible**: Drop-in replacement

**Cons**:
- Requires GPU (8GB+ VRAM)
- More complex setup
- Higher memory overhead

**API Example**:
```bash
POST http://vllm:8000/v1/chat/completions
{
  "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
  "messages": [
    {"role": "user", "content": "List all tickets"}
  ]
}
```

**Interview Question**: *When to use Ollama vs vLLM?*
- **Ollama**: Development, demos, CPU-only environments, small teams
- **vLLM**: Production, high-throughput, GPU clusters, >100 req/min

### Implementation (Abstraction)
```python
class LLMProvider:
    """Abstraction layer for any LLM provider"""
    
    @staticmethod
    def create(provider: str, base_url: str, model: str):
        if provider == "ollama":
            return OllamaClient(base_url, model)
        elif provider == "vllm":
            return VLLMClient(base_url, model)
        elif provider == "openai":
            return OpenAIClient(api_key, model)
    
    async def chat(self, messages: List[Dict]) -> str:
        raise NotImplementedError

class OllamaClient(LLMProvider):
    async def chat(self, messages: List[Dict]) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages}
            )
            return response.json()["message"]["content"]

class VLLMClient(LLMProvider):
    async def chat(self, messages: List[Dict]) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={"model": self.model, "messages": messages}
            )
            return response.json()["choices"][0]["message"]["content"]
```

---

## Request Flow & Orchestration

### End-to-End Request Flow

```
1. User sends: "Show me all open tickets"
   POST http://localhost:8080/orchestrate
   {"query": "Show me all open tickets", "user": {"id": "user123", "role": "support_agent"}}

2. Orchestrator receives request
   - Logs request
   - Validates input

3. Capability Retrieval (RAG)
   POST http://mcp-embed:9001/search
   {"query": "Show me all open tickets", "top_k": 3}
   
   Response:
   [
     {"name": "list_tickets", "score": 0.95, "description": "..."},
     {"name": "get_ticket", "score": 0.72, "description": "..."}
   ]

4. LLM Reasoning
   POST http://ollama:11434/api/chat
   {
     "messages": [
       {"role": "system", "content": "You are an API assistant. Available tools: list_tickets, get_ticket..."},
       {"role": "user", "content": "Show me all open tickets"}
     ]
   }
   
   LLM Response:
   "I will use the list_tickets tool with filter: status=open"
   
   (Or structured JSON if using function calling)

5. Policy Check
   POST http://mcp-policy:8181/v1/data/nl_api/authz/allow
   {"input": {"tool": "list_tickets", "user": {"role": "support_agent"}}}
   
   Response: {"result": true}

6. Tool Execution
   POST http://mcp-api:9000/execute
   {"tool": "list_tickets", "parameters": {"status": "open"}}
   
   → MCP service calls actual API →
   GET https://api.example.com/tickets?status=open
   
   Response: [{"id": 1, "title": "Bug report", ...}, ...]

7. Response Aggregation
   Orchestrator sends result back to LLM for natural language formatting:
   
   POST http://ollama:11434/api/chat
   {
     "messages": [
       ...,
       {"role": "assistant", "content": "I will use list_tickets..."},
       {"role": "tool", "content": "[{\"id\": 1, \"title\": \"Bug report\"}]"},
       {"role": "user", "content": "Format this for the user"}
     ]
   }
   
   LLM Response:
   "Here are the open tickets:\n1. Bug report (ID: 1)\n..."

8. Return to User
   Response: {"result": "Here are the open tickets:...", "success": true}
```

---

## Common Interview Questions

### Q1: What is the difference between RAG and fine-tuning?
**Answer**:
- **Fine-tuning**: Updates model weights with new training data. Expensive, slow, risk of catastrophic forgetting.
- **RAG**: Retrieves external knowledge at inference time. Fast, scalable, up-to-date data.

**When to use each**:
- Fine-tuning: Specialized language (medical, legal), style adaptation
- RAG: Dynamic data (APIs, documents), factual accuracy

### Q2: How do you handle LLM hallucinations?
**Answer**:
1. **RAG**: Ground responses in retrieved facts
2. **Structured output**: Force JSON schemas, not free text
3. **Validation**: Check responses against expected formats
4. **Policy enforcement**: OPA prevents invalid tool calls
5. **Confidence scores**: Only execute if retrieval score > threshold (e.g., 0.7)

### Q3: Why async/await instead of threads?
**Answer**:
- **Async**: Single thread, event loop, 10k+ concurrent connections
- **Threads**: OS overhead, context switching, max ~1k threads
- **Use case**: I/O-bound tasks (HTTP calls, database queries)

### Q4: How do you scale this system?
**Answer**:
1. **Horizontal scaling**: Run multiple orchestrator replicas behind load balancer
2. **Caching**: Cache embeddings, LLM responses (Redis)
3. **Batching**: Batch multiple requests to LLM
4. **GPU parallelism**: vLLM tensor parallelism for large models
5. **Database**: Move capability storage to PostgreSQL with pgvector

### Q5: What are security risks and mitigations?
**Risks**:
1. **Prompt injection**: User tricks LLM into calling wrong tools
   - Mitigation: OPA policies, input validation, allowlists
2. **Data leakage**: LLM exposes sensitive data
   - Mitigation: Redaction, role-based access control (RBAC)
3. **API abuse**: Excessive calls to external APIs
   - Mitigation: Rate limiting, cost tracking

### Q6: How do you monitor this system?
**Answer** (for production, not POC):
1. **Metrics**: Prometheus (request rate, latency, error rate)
2. **Tracing**: Jaeger (distributed trace across services)
3. **Logs**: Loki + Grafana (structured logs, log aggregation)
4. **Alerts**: Alertmanager (high error rate, slow responses)

### Q7: What is semantic search?
**Answer**:
- **Keyword search**: Exact word matching ("list tickets" ≠ "show tickets")
- **Semantic search**: Meaning-based ("list tickets" ≈ "show tickets" ≈ "display issues")
- **How**: Embeddings capture semantic meaning, cosine similarity measures closeness

### Q8: Explain the MCP protocol
**Answer**:
MCP standardizes how LLMs call external tools:
1. **Tool discovery**: LLM queries available tools
2. **Tool description**: Each tool has name, description, input schema
3. **Tool invocation**: LLM provides parameters, system executes
4. **Result handling**: System returns structured result to LLM

Benefits: Interoperability, security, auditability

---

## Key Takeaways for Interviews

### Architecture Decisions
1. **Microservices**: Independent scaling, fault isolation
2. **Async**: High concurrency for I/O-bound tasks
3. **RAG over fine-tuning**: Dynamic, up-to-date, cheaper
4. **Policy enforcement**: Security-first design

### Technology Choices
1. **FastAPI**: Modern, async, auto-docs (OpenAPI)
2. **Ollama**: Easy local development
3. **FAISS**: Fast similarity search (C++ optimized)
4. **OPA**: Declarative policies, battle-tested

### Production Considerations
1. **Monitoring**: Metrics, traces, logs (not in POC)
2. **Scaling**: Horizontal scaling, caching, batching
3. **Security**: Allowlists, RBAC, input validation
4. **Cost**: Token tracking, rate limiting

### Performance
- **Orchestrator**: 50-200ms (excluding LLM)
- **LLM (Ollama)**: 1-5 seconds (CPU), 500ms-2s (GPU)
- **LLM (vLLM)**: 200-800ms (GPU optimized)
- **Embedding**: 10-50ms per query
- **Total**: 1.5-5 seconds end-to-end

---

## Hands-On Demo Script

### Setup
```bash
cd nl-api-orchestrator
docker-compose -f docker-compose.poc.yml up -d
docker exec -it nl-api-orchestrator-ollama-1 ollama pull llama3.1:8b
```

### Test Request
```bash
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "List all open tickets",
    "user": {"id": "demo", "role": "support_agent"}
  }'
```

### Show Logs
```bash
docker-compose -f docker-compose.poc.yml logs -f orchestrator
```

### Explain During Interview
1. "User sends natural language query"
2. "Orchestrator uses RAG to find relevant tools"
3. "LLM reasons about which tool to call"
4. "Policy engine validates access"
5. "MCP service executes the API call"
6. "LLM formats the response naturally"

---

This guide covers the depth needed for senior roles. Focus on:
- **Why** decisions were made (not just **what**)
- **Trade-offs** (Ollama vs vLLM, RAG vs fine-tuning)
- **Production concerns** (scaling, security, monitoring)
- **Hands-on knowledge** (show the code, explain the flow)

Good luck with your interviews! 🚀

