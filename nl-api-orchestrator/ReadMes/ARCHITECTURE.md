# Architecture Deep Dive

## Overview

The NL → API Orchestrator is a production-grade system that transforms natural language queries into structured API calls. It combines Retrieval-Augmented Generation (RAG), Large Language Model (LLM) reasoning, policy enforcement, and secure API execution in a containerized microservices architecture.

## Core Components

### 1. Orchestrator Service (FastAPI)

**Location:** `orchestrator/`

**Responsibilities:**
- Accept natural language queries via REST API
- Coordinate the entire orchestration flow
- Manage state and session tracking
- Emit observability signals (logs, traces, metrics)

**Key Modules:**
- `app.py` - Main FastAPI application with /orchestrate endpoint
- `retriever.py` - RAG capability retrieval
- `tool_router.py` - LLM-based tool selection and payload generation
- `validators.py` - JSON Schema validation
- `normalizers.py` - Payload normalization (synonyms, formats)
- `mcp_client.py` - Client for MCP API tools
- `opa_client.py` - Client for OPA policy checks

### 2. MCP Embeddings Server

**Location:** `mcp/embed_tools/`

**Responsibilities:**
- Generate embeddings for text using SentenceTransformers
- Maintain FAISS vector index of capabilities
- Provide similarity search for capability retrieval

**Technology Stack:**
- SentenceTransformers (BAAI/bge-small-en-v1.5)
- FAISS for efficient vector search
- FastAPI for HTTP endpoints

**Endpoints:**
- `POST /embed` - Generate embedding for text
- `POST /search` - Find similar capabilities via vector search
- `GET /health` - Health check

**Index Building:**
At startup, the server:
1. Loads `capabilities.json`
2. Combines name, description, and examples into rich text
3. Generates embeddings for each capability
4. Builds FAISS index with normalized vectors (cosine similarity)

### 3. MCP API Tools Server

**Location:** `mcp/api_tools/`

**Responsibilities:**
- Expose business API tools as standardized HTTP endpoints
- Enforce URL allowlisting
- Execute upstream API calls
- Mock responses for demo purposes

**Tool Architecture:**
Each tool is a Python async function with signature:
```python
async def tool_name(args: Dict, allowlist: List[str], token: str) -> Dict
```

**Security:**
- Every outbound URL is checked against `ALLOWLIST_PREFIXES`
- Authentication tokens passed securely
- Timeout enforcement (30s default)

**Endpoints:**
- `POST /tools/list` - List available tools with schemas
- `POST /tools/invoke` - Invoke a tool with arguments
- `GET /health` - Health check

### 4. OPA Policy Engine

**Location:** `mcp/policy/`

**Responsibilities:**
- Evaluate policies before tool execution
- Risk-based decision making
- Confirmation requirements for high-risk operations

**Policy Rules:**
- **Low Risk:** Allow with valid payload
- **Medium Risk:** Require description ≥ 10 chars
- **High Risk:** Require explicit confirmation + description ≥ 20 chars

**Input Schema:**
```json
{
  "payload": {...},
  "tool": "tool_name",
  "risk": "low|medium|high",
  "confirmed": true|false,
  "user": "user_id"
}
```

**Output Schema:**
```json
{
  "allow": true|false,
  "reason": "explanation if denied"
}
```

### 5. Capability Registry

**Location:** `orchestrator/registry/capabilities.json`

**Structure:**
```json
{
  "name": "tool_name",
  "description": "What this tool does",
  "endpoint": "HTTP_METHOD url",
  "auth": "bearer|none",
  "risk": "low|medium|high",
  "input_schema": {...},
  "examples": [...]
}
```

**Best Practices:**
- Rich descriptions for better RAG retrieval
- Multiple examples covering edge cases
- Complete JSON Schemas with validation rules
- Clear risk classification

## Data Flow

### Happy Path: Complete Query

```
1. User → POST /orchestrate {"query": "Open urgent ticket for payment failure"}
   
2. Orchestrator → Embed Server
   POST /embed {"text": "Open urgent ticket..."}
   ← {"vector": [...]}
   
3. Orchestrator → Embed Server
   POST /search {"vector": [...], "top_k": 3}
   ← {"ids": ["create_ticket", ...], "scores": [0.95, ...]}
   
4. Orchestrator → LLM (vLLM/Ollama)
   Chat completion with:
   - System prompt (instructions + JSON schema)
   - User prompt (query + candidate tools)
   ← {"decision": "USE_TOOL", "tool_name": "create_ticket", "payload": {...}}
   
5. Orchestrator → Validate payload against capability schema
   ✓ Valid
   
6. Orchestrator → Normalize payload (synonyms, formats)
   "asap" → "urgent"
   
7. Orchestrator → OPA
   POST /v1/data/policy/allow {"input": {payload, tool, risk, confirmed, user}}
   ← {"result": {"allow": true}}
   
8. Orchestrator → API Tools
   POST /tools/invoke {"tool": "create_ticket", "args": {...}}
   ← {"status": "ok", "ticket_id": "TKT-12345"}
   
9. Orchestrator → User
   {
     "decision": "USE_TOOL",
     "tool_used": "create_ticket",
     "api_result": {"ticket_id": "TKT-12345"},
     "message": "Created ticket TKT-12345 successfully."
   }
```

### Edge Case: Missing Information

```
1. User → POST /orchestrate {"query": "Create a ticket"}
   
2-4. [Same RAG + LLM flow]
   
5. LLM Response:
   {
     "decision": "ASK_USER",
     "tool_name": "create_ticket",
     "missing_fields": ["title", "description", "priority"]
   }
   
6. Orchestrator → User
   {
     "decision": "ASK_USER",
     "missing_fields": ["title", "description", "priority"],
     "message": "I need more information to create_ticket. Please provide: title, description, priority"
   }
```

### Edge Case: Policy Denial

```
1-6. [Normal flow up to policy check]
   
7. Orchestrator → OPA
   ← {"result": {"allow": false, "reason": "High-risk operation requires explicit confirmation"}}
   
8. Orchestrator → User
   {
     "decision": "ASK_USER",
     "message": "This is a high-risk operation. High-risk operation requires explicit confirmation. Please confirm.",
     "confirm_fields": {...}
   }
```

## LLM Integration

### Prompt Engineering

**System Prompt:**
- Clear instructions on available decisions (USE_TOOL, ASK_USER, NONE)
- Strict JSON response schema
- Examples for each decision type
- Rules for parameter extraction

**User Prompt:**
- User's query
- Candidate tool descriptions
- JSON Schemas for each tool
- 1-2 examples per tool

**Response Format:**
- Use `response_format={"type": "json_object"}` when supported
- Fallback to JSON repair if model doesn't support JSON mode
- Validate response against expected schema

### LLM Provider Support

**vLLM (default):**
- Faster inference
- OpenAI-compatible API
- GPU acceleration required
- Better for production

**Ollama (alternative):**
- Easier model management
- CPU/GPU support
- Good for development
- Slightly slower

**Switching:**
```env
# Ollama (default)
LLM_PROVIDER=ollama
OPENAI_BASE_URL=http://ollama:11434/v1
MODEL_NAME=llama3.1:8b

# vLLM (alternative)
LLM_PROVIDER=vllm
OPENAI_BASE_URL=http://vllm:8000/v1
MODEL_NAME=meta-llama/Meta-Llama-3.1-8B-Instruct
```

## Security Architecture

### 1. URL Allowlisting

**Implementation:** `mcp/api_tools/src/server.py`

```python
def is_allowed(url: str) -> bool:
    return any(url.startswith(prefix) for prefix in ALLOWLIST_PREFIXES)
```

**Configuration:**
```env
ALLOWLIST_PREFIXES=https://api.example.com/,https://internal.corp/api/
```

**Enforcement:** Every outbound HTTP request is checked before execution.

### 2. JSON Schema Validation

**Implementation:** `orchestrator/src/validators.py`

Uses `jsonschema` library with Draft7Validator for:
- Type checking
- Required fields
- String length constraints
- Enum validation
- Pattern matching
- Format validation (email, URL, etc.)

### 3. Payload Normalization

**Implementation:** `orchestrator/src/normalizers.py`

**Purpose:**
- Reduce LLM hallucination impact
- Handle common synonyms
- Standardize formats

**Example Mappings:**
```python
PRIORITY_MAP = {
    "asap": "urgent",
    "critical": "urgent",
    "normal": "medium"
}

STATUS_MAP = {
    "active": "open",
    "done": "closed"
}
```

### 4. Policy Enforcement (OPA)

**Benefits:**
- Declarative policy language (Rego)
- Centralized policy management
- Auditable decisions
- Easy to update without code changes

**Example Policy:**
```rego
allow {
    input.risk == "medium"
    input.payload.description
    count(input.payload.description) >= 10
}
```

### 5. Authentication & Authorization

**Current:** Token-based (demo)

**Production Recommendations:**
- JWT tokens with claims
- OAuth2/OIDC integration
- Per-user capability filtering
- Audit logging of all tool invocations

## Observability

### 1. Structured Logging

**Format:** JSON with correlation IDs

**Example:**
```json
{
  "timestamp": "2026-02-12T14:30:00Z",
  "level": "INFO",
  "service": "orchestrator",
  "session_id": "abc123",
  "message": "Invoking tool: create_ticket"
}
```

**Aggregation:** Loki + Promtail

### 2. Distributed Tracing

**Technology:** OpenTelemetry → Jaeger

**Spans:**
- `orchestrate` (root)
  - `retrieve_capabilities`
  - `llm_reasoning`
  - `validate_payload`
  - `normalize_payload`
  - `policy_check`
  - `execute_tool`

**Benefits:**
- End-to-end request tracking
- Latency breakdown
- Error attribution

### 3. Metrics

**Technology:** Prometheus

**Key Metrics:**
- `orchestrator_requests_total{decision, tool}` - Counter
- `orchestrator_request_duration_seconds` - Histogram
- `orchestrator_llm_tokens_total{type}` - Counter

**Dashboards:** Pre-built Grafana dashboard with:
- Request rate by decision
- P50/P95 latencies
- Decision distribution
- LLM token usage

### 4. Alerts (Production)

**Recommended:**
- High error rate (>5%)
- P95 latency > 10s
- Policy denial rate spike
- Service down

## Scalability

### Horizontal Scaling

**Stateless Services:**
- Orchestrator: Scale to N replicas
- API Tools: Scale independently
- Embed Server: Read-only, scale for throughput

**Stateful Services:**
- vLLM: GPU-bound, scale with GPU resources
- FAISS: In-memory, consider distributed index for large registries

### Performance Optimization

**Caching:**
- Embed query results (Redis)
- LLM responses for common queries (with TTL)
- Capability registry in-memory

**Batching:**
- Batch LLM requests if using shared vLLM
- Batch embeddings for multiple queries

**Timeouts:**
- LLM: 30s
- API Tools: 30s
- Policy: 10s
- Embed: 10s

### Resource Requirements

**Minimum:**
- 16GB RAM (for vLLM with 8B model)
- 1 GPU (for vLLM)
- 4 CPU cores

**Recommended:**
- 32GB RAM
- 1 GPU (24GB VRAM)
- 8 CPU cores
- SSD storage for model cache

## Extension Points

### Adding New Tools

1. **Create tool function:**
   ```python
   # mcp/api_tools/src/tools/new_tool.py
   async def new_tool(args: Dict, allowlist: list, token: str) -> Dict:
       # Implementation
       pass
   ```

2. **Register tool:**
   ```python
   # mcp/api_tools/src/tools/__init__.py
   from .new_tool import new_tool
   TOOLS["new_tool"] = new_tool
   ```

3. **Add capability card:**
   ```json
   // orchestrator/registry/capabilities.json
   {
     "name": "new_tool",
     "description": "...",
     "input_schema": {...},
     "examples": [...]
   }
   ```

4. **Rebuild:**
   ```bash
   docker compose up -d --build mcp-api orchestrator
   ```

### Custom Normalizers

```python
# orchestrator/src/normalizers.py
from normalizers import add_synonym

add_synonym(PRIORITY_MAP, "now", "urgent")
```

### Custom Policies

Edit `mcp/policy/policy.rego`:
```rego
# Require manager approval for deletions
allow {
    input.tool == "delete_resource"
    input.user.role == "manager"
}
```

Restart OPA:
```bash
docker compose restart mcp-policy
```

## Testing Strategy

### Unit Tests

**Location:** `orchestrator/tests/`

**Coverage:**
- Payload validation
- Normalization logic
- Tool routing
- Error handling

**Run:**
```bash
docker compose run --rm orchestrator pytest tests/ -v
```

### Integration Tests

**E2E Tests:** `test.sh` / `test.ps1`

**Scenarios:**
- Happy path orchestration
- Missing information handling
- No matching tool
- Priority normalization
- Filtered searches

### Load Testing

**Recommended Tools:**
- Locust for HTTP load testing
- Monitor with Grafana during tests
- Target: 100 RPS sustained

## Production Checklist

- [ ] Replace demo API with real endpoints
- [ ] Configure production allowlist
- [ ] Implement proper authentication (JWT/OAuth)
- [ ] Set up monitoring alerts
- [ ] Enable HTTPS/TLS
- [ ] Configure rate limiting
- [ ] Set up log retention policies
- [ ] Backup capability registry
- [ ] Document runbooks
- [ ] Perform security audit
- [ ] Load test at scale
- [ ] Set up CI/CD pipeline

## Troubleshooting

### vLLM Out of Memory

**Solution:** Use smaller model or quantization:
```env
MODEL_NAME=meta-llama/Meta-Llama-3.1-8B-Instruct-AWQ
```

### LLM Not Returning JSON

**Solution:** Check prompt in `prompts.py`, add more examples, or use model with better JSON support.

### Slow Embeddings

**Solution:** 
- Use smaller embedding model
- Reduce registry size
- Cache embeddings

### Policy Always Denying

**Solution:**
- Check OPA logs: `docker compose logs mcp-policy`
- Test policy with OPA playground
- Verify input format matches policy expectations

## Future Enhancements

1. **Multi-turn Conversations:** Session state management
2. **Tool Composition:** Chain multiple tools automatically
3. **Streaming Responses:** SSE for real-time updates
4. **Model Fine-tuning:** Train on capability-specific data
5. **Advanced RAG:** Hybrid search (vector + keyword)
6. **A/B Testing:** Compare prompt/model variations
7. **Human-in-the-loop:** Approval workflows for high-risk ops
8. **API Versioning:** Support multiple capability versions
9. **Feedback Loop:** Learn from user corrections
10. **Multi-tenancy:** Per-tenant capabilities and policies

---

For questions or contributions, see README.md.

