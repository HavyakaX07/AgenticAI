# Complete Interview Guide: Agentic RAG with MCP for NMS API Orchestration

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Deep Dive](#architecture-deep-dive)
3. [Core Components Explained](#core-components-explained)
4. [RAG (Retrieval-Augmented Generation)](#rag-retrieval-augmented-generation)
5. [MCP (Model Context Protocol)](#mcp-model-context-protocol)
6. [LLM Integration](#llm-integration)
7. [Policy Enforcement (OPA)](#policy-enforcement-opa)
8. [Request Flow](#request-flow)
9. [Design Decisions](#design-decisions)
10. [Interview Questions & Answers](#interview-questions--answers)

---

## System Overview

### What is This System?
This is an **Agentic NMS (Network Management System) API Orchestrator** that converts natural language queries into executable API calls for network device credential management. It uses:

- **RAG (Retrieval-Augmented Generation)**: To find relevant API capabilities from a registry
- **LLM (Large Language Model)**: To understand natural language and make intelligent decisions
- **MCP (Model Context Protocol)**: To execute API tools in a standardized way
- **OPA (Open Policy Agent)**: To enforce security policies before execution

### Key Features
1. **Natural Language Understanding**: Users can say "copy credentials from router-01 to switch-02" instead of writing API calls
2. **Conversational AI**: Handles greetings, help requests, and chitchat naturally
3. **Intelligent Tool Selection**: Uses RAG + LLM to pick the right API from many options
4. **Policy Enforcement**: Prevents unauthorized or risky operations
5. **Parameter Extraction**: Automatically fills API parameters from natural language
6. **Validation**: Ensures all parameters meet schema requirements before execution

---

## Architecture Deep Dive

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Query (NL)                           │
│              "Copy credentials from R1 to S1, S2"                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR (FastAPI)                         │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 1: RAG - Capability Retrieval                        │  │
│  │ ┌────────────────┐  ┌──────────────────────────────┐    │  │
│  │ │ User Query     │→│ Embedding Service (MCP)       │    │  │
│  │ │ Embedding      │  │ (sentence-transformers)       │    │  │
│  │ └────────────────┘  └──────────────────────────────┘    │  │
│  │         │                                                 │  │
│  │         ▼                                                 │  │
│  │ ┌────────────────────────────────────────────────────┐  │  │
│  │ │ Semantic Search: Top-K Similar Capabilities        │  │  │
│  │ │ Registry: capabilities.json + metadata             │  │  │
│  │ └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 2: LLM - Tool Selection & Parameter Extraction      │  │
│  │ ┌────────────────────────────────────────────────────┐  │  │
│  │ │ LLM (Ollama/vLLM)                                  │  │  │
│  │ │ - Analyzes: Query + Top-K Capabilities            │  │  │
│  │ │ - Decides: USE_TOOL / ASK_USER / GENERAL / NONE   │  │  │
│  │ │ - Extracts: Parameters from natural language       │  │  │
│  │ └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 3: Validation                                        │  │
│  │ - JSON Schema validation against capability schema       │  │
│  │ - Type checking, range validation, required fields       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 4: Normalization                                     │  │
│  │ - lowercase emails, trim whitespace                       │  │
│  │ - Apply field-specific normalizations                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 5: Policy Check (OPA)                                │  │
│  │ ┌────────────────────────────────────────────────────┐  │  │
│  │ │ Open Policy Agent                                  │  │  │
│  │ │ - Risk level: low/medium/high/critical            │  │  │
│  │ │ - User confirmation for high-risk ops             │  │  │
│  │ │ - Returns: allow/deny + reason                    │  │  │
│  │ └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 6: Tool Execution (MCP)                              │  │
│  │ ┌────────────────────────────────────────────────────┐  │  │
│  │ │ MCP API Tools Server                               │  │  │
│  │ │ - Invokes actual API endpoints                     │  │  │
│  │ │ - Handles authentication                           │  │  │
│  │ │ - Returns structured results                       │  │  │
│  │ └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Step 7: Response Generation                               │  │
│  │ - Create user-friendly message                            │  │
│  │ - Include execution results                               │  │
│  │ - Session management for multi-turn conversation          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Response to User (JSON)                       │
│  {                                                               │
│    "decision": "USE_TOOL",                                       │
│    "tool_used": "copy_device_credentials",                       │
│    "message": "Successfully copied credentials...",              │
│    "api_result": {...}                                           │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components Explained

### 1. **Orchestrator (app_poc.py)**

**Purpose**: Main application that coordinates all components

**Key Responsibilities**:
- Receives user queries via REST API (`/orchestrate` endpoint)
- Orchestrates the 7-step pipeline
- Manages session state for multi-turn conversations
- Handles errors and edge cases

**Why FastAPI?**
- Asynchronous support for concurrent requests
- Automatic API documentation (Swagger/OpenAPI)
- Pydantic models for request/response validation
- Fast performance for production use

**Key Code Flow**:
```python
@app.post("/orchestrate")
async def orchestrate(request: OrchestrationRequest):
    # Step 1: RAG retrieval
    candidates = await retriever.retrieve(query, top_k=3)
    
    # Step 2: LLM decision
    llm_response = await router.route(query, candidates)
    
    # Handle different decisions
    if decision == "GENERAL_RESPONSE":
        return conversational_response
    elif decision == "ASK_USER":
        return ask_for_missing_fields
    elif decision == "USE_TOOL":
        # Step 3-7: Validate, normalize, policy check, execute
        ...
```

---

### 2. **RAG - Capability Retriever (retriever.py)**

**Purpose**: Find the most relevant API capabilities for a given query

**How It Works**:
1. **Initialization**: Loads `capabilities.json` with all available API tools
2. **Embedding**: Converts user query to vector using embedding model
3. **Semantic Search**: Compares query embedding with pre-computed capability embeddings
4. **Ranking**: Returns top-K most similar capabilities

**Why This Approach?**
- **Scalability**: Can handle 100s or 1000s of APIs without performance degradation
- **Semantic Understanding**: Matches intent, not just keywords (e.g., "show" matches "retrieve")
- **Accuracy**: Reduces hallucination by providing relevant context to LLM

**Embedding Model**:
- **Model**: `BAAI/bge-small-en-v1.5` (384 dimensions)
- **Why**: Fast, accurate for semantic search, small memory footprint
- **Server**: MCP embed_tools service via HTTP

**Code Example**:
```python
class CapabilityRetriever:
    async def retrieve(self, query: str, top_k: int = 3):
        # Get query embedding
        query_emb = await self.embed_server.embed(query)
        
        # Compute cosine similarity with all capabilities
        similarities = cosine_similarity(query_emb, self.capability_embeddings)
        
        # Return top-K
        top_indices = np.argsort(similarities)[-top_k:]
        return [self.capabilities[i] for i in top_indices]
```

---

### 3. **LLM Router (tool_router.py)**

**Purpose**: Use LLM to select the right tool and extract parameters

**Why LLM After RAG?**
- **RAG provides context**: Narrows down from 100s to 3-5 relevant tools
- **LLM makes final decision**: Understands nuances, handles ambiguity
- **Parameter extraction**: Converts "router-01 and switch-02" → `["router-01", "switch-02"]`

**LLM Provider**:
- **Ollama** (POC): Local, fast startup, good for development
- **vLLM** (Production): Optimized inference, batching, higher throughput

**Prompt Engineering**:
- **System Prompt**: Defines role as NMS orchestrator, decision types, JSON format
- **User Prompt**: Includes query + top-K capabilities with schemas and examples
- **Output**: Structured JSON with decision, tool_name, payload, etc.

**Decision Types**:
1. **USE_TOOL**: All info present, ready to execute
2. **ASK_USER**: Missing required fields, need more info
3. **GENERAL_RESPONSE**: Greeting/thanks/chitchat, no tool needed
4. **NONE**: No relevant tool available

**Code Example**:
```python
class ToolRouter:
    async def route(self, query: str, capabilities: list):
        messages = create_messages(query, capabilities)
        
        response = await self.llm_client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.0,  # Deterministic for tool selection
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
```

---

### 4. **MCP (Model Context Protocol)**

**Purpose**: Standardized protocol for tool execution

**Why MCP?**
- **Separation of Concerns**: Tool execution logic separate from orchestration
- **Reusability**: Same tools can be used by multiple agents/LLMs
- **Extensibility**: Easy to add new tools without modifying orchestrator
- **Type Safety**: Tools declare input/output schemas

**MCP Components**:

#### a) **MCP Client (mcp_client.py)**
```python
class MCPClient:
    async def invoke_tool(self, tool_name: str, params: dict):
        response = await httpx.post(
            f"{self.api_tools_url}/invoke",
            json={"tool": tool_name, "params": params}
        )
        return response.json()
```

#### b) **MCP API Tools Server (mcp/api_tools/server.py)**
- Receives tool invocation requests
- Maps tool names to actual API implementations
- Handles authentication, retries, error handling
- Returns structured results

#### c) **MCP Embed Tools Server (mcp/embed_tools/server.py)**
- Provides embedding service via MCP
- Loads sentence-transformers model
- Exposes `/embed` endpoint for vectorization

**Why Separate Servers?**
- **Resource isolation**: Embedding model uses GPU, API tools don't
- **Scaling**: Can scale embed server independently based on load
- **Development**: Can update tools without restarting embedding service

---

### 5. **Validation & Normalization**

#### **Validation (validators.py)**
**Purpose**: Ensure parameters meet schema requirements

**Checks**:
- **Type validation**: string, integer, boolean, array, object
- **Required fields**: All required parameters present
- **Constraints**: min/max length, enum values, regex patterns

**JSON Schema Example**:
```json
{
  "type": "object",
  "properties": {
    "device_id": {"type": "string", "minLength": 1},
    "priority": {"type": "string", "enum": ["low", "medium", "high"]}
  },
  "required": ["device_id", "priority"]
}
```

#### **Normalization (normalizers.py)**
**Purpose**: Clean and standardize parameter values

**Transformations**:
- Lowercase emails: `User@Example.COM` → `user@example.com`
- Trim whitespace: `" router-01 "` → `"router-01"`
- Date formatting: `12/31/2024` → `2024-12-31`

**Why Normalize?**
- **Consistency**: API expects specific formats
- **Error prevention**: Avoid failures due to formatting issues
- **Better matching**: Normalized values match better in databases

---

### 6. **Policy Enforcement (OPA)**

**Purpose**: Security and authorization checks before execution

**Why OPA (Open Policy Agent)?**
- **Declarative policies**: Write policies in Rego language
- **Separation of concerns**: Policy logic separate from application code
- **Centralized**: Single source of truth for all policy decisions
- **Auditable**: All policy decisions are logged

**Policy Rules (policy.rego)**:
```rego
# Always allow low-risk operations
allow if {
    input.risk == "low"
}

# High-risk operations require confirmation
allow if {
    input.risk == "high"
    input.confirmed == true
}

# Critical operations require admin role
allow if {
    input.risk == "critical"
    input.user.role == "admin"
    input.confirmed == true
}
```

**Policy Input Example**:
```json
{
  "tool": "copy_device_credentials",
  "risk": "medium",
  "confirmed": false,
  "user": "default_user",
  "payload": {...}
}
```

**Policy Output**:
```json
{
  "allow": true,
  "reason": "Medium-risk operation allowed"
}
```

---

## RAG (Retrieval-Augmented Generation)

### Why RAG for API Orchestration?

**Problems RAG Solves**:
1. **Context Length Limits**: Can't fit 100s of API schemas in LLM prompt
2. **Hallucination**: LLM might invent APIs that don't exist
3. **Cost**: Processing large prompts is expensive
4. **Performance**: Semantic search is faster than LLM for retrieval

**RAG vs. Fine-tuning**:
| Aspect | RAG | Fine-tuning |
|--------|-----|-------------|
| **Dynamic Updates** | Add APIs without retraining | Requires retraining |
| **Cost** | Low (embedding only) | High (GPU, time) |
| **Accuracy** | High (exact schema retrieval) | May hallucinate |
| **Latency** | Fast (sub-second) | Fast inference, slow training |

### RAG Implementation Details

**1. Capability Registry Structure**:
```json
[
  {
    "name": "copy_device_credentials",
    "description": "Copy credentials from source device to multiple destinations",
    "endpoint": "POST /api/devices/credentials/copy",
    "auth": "bearer",
    "risk": "medium",
    "input_schema": {
      "type": "object",
      "properties": {
        "source_device": {"type": "string"},
        "destination_devices": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["source_device", "destination_devices"]
    },
    "examples": [
      {
        "user": "Copy credentials from router-01 to switch-02",
        "payload": {
          "source_device": "router-01",
          "destination_devices": ["switch-02"]
        }
      }
    ]
  }
]
```

**2. Embedding Strategy**:
- **What to embed**: `name + description + examples`
- **Why**: Captures semantic meaning from multiple angles
- **Caching**: Pre-compute embeddings at startup, store in memory

**3. Similarity Metric**:
- **Cosine Similarity**: Measures angle between vectors (0 to 1)
- **Why**: Works well for normalized embeddings, fast computation
- **Threshold**: Typically 0.7+ for relevant matches

**4. Top-K Selection**:
- **K=3**: Good balance between context and specificity
- **Why not K=1**: Gives LLM options to choose from
- **Why not K=10**: Too much context, confuses LLM

---

## MCP (Model Context Protocol)

### What is MCP?

MCP is an **open protocol** for standardized communication between LLMs/agents and external tools/data sources.

**Core Concepts**:
1. **Tools**: Functions that can be invoked (APIs, databases, scripts)
2. **Resources**: Data that can be read (files, configs, knowledge bases)
3. **Prompts**: Reusable prompt templates
4. **Servers**: Services that expose tools/resources via MCP
5. **Clients**: Applications that use MCP servers

### Why MCP for This Project?

**Without MCP**:
- Hard-coded API calls in orchestrator
- Tight coupling between orchestrator and APIs
- Difficult to add new APIs
- No standardization

**With MCP**:
- Declarative tool definitions
- Loose coupling via protocol
- Easy extensibility (add new servers)
- Consistent interface for all tools

### MCP Architecture in This Project

```
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator                           │
│                   (MCP Client)                           │
└───────────────┬─────────────────────┬───────────────────┘
                │                     │
                │                     │
     ┌──────────▼──────────┐   ┌─────▼──────────────────┐
     │  MCP Embed Server   │   │  MCP API Tools Server  │
     │                     │   │                        │
     │  Tools:             │   │  Tools:                │
     │  - embed_text       │   │  - copy_credentials    │
     │  - embed_batch      │   │  - get_credentials     │
     │                     │   │  - update_credentials  │
     │  Model:             │   │  - list_devices        │
     │  - bge-small-en     │   │  ...                   │
     └─────────────────────┘   └────────────────────────┘
```

### MCP Tool Definition Example

```json
{
  "name": "copy_device_credentials",
  "description": "Copy authentication credentials from a source device to one or more destination devices",
  "inputSchema": {
    "type": "object",
    "properties": {
      "source_device": {
        "type": "string",
        "description": "Device ID or name of the source device"
      },
      "destination_devices": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of destination device IDs or names"
      }
    },
    "required": ["source_device", "destination_devices"]
  }
}
```

---

## LLM Integration

### Ollama vs. vLLM

| Feature | Ollama | vLLM |
|---------|--------|------|
| **Use Case** | Development, POC | Production |
| **Setup** | Simple, single command | Requires configuration |
| **Performance** | Good | Excellent (optimized) |
| **Features** | Basic | Advanced (batching, paging) |
| **Memory** | Higher per request | Efficient (KV cache) |
| **Concurrency** | Limited | High (continuous batching) |

### Why Ollama for POC?

```yaml
# docker-compose.poc.yml
ollama:
  image: ollama/ollama:latest
  command: serve
  ports:
    - "11434:11434"
  environment:
    - OLLAMA_MODELS=qwen2.5:3b  # Fast, lightweight model
```

**Benefits**:
- Zero configuration
- Auto-downloads models
- Fast startup (<30 seconds)
- Low resource requirements

### Prompt Design Philosophy

**1. System Prompt**:
- Defines agent identity (NMS orchestrator)
- Lists available decisions
- Specifies output format (JSON)
- Provides rules and constraints

**2. User Prompt**:
- User query
- Top-K capabilities with full schemas
- Examples from each capability
- Clear task instruction

**3. Temperature = 0.0**:
- Deterministic responses
- Critical for tool selection (not creative writing)
- Ensures consistent JSON formatting

**4. Response Format**:
```json
{
  "decision": "USE_TOOL",
  "tool_name": "copy_device_credentials",
  "payload": {
    "source_device": "router-01",
    "destination_devices": ["switch-02", "switch-03"]
  },
  "notes": "Extracted 3 devices from query"
}
```

---

## Request Flow

### Example 1: Tool Execution

**User Query**: "Copy credentials from router-01 to switch-02 and switch-03"

**Step-by-Step**:

1. **RAG Retrieval**:
   - Query embedding: `[0.23, -0.15, 0.87, ...]`
   - Top-3 capabilities: `copy_device_credentials`, `bulk_update_credentials`, `clone_device_config`
   - Top match: `copy_device_credentials` (similarity: 0.92)

2. **LLM Decision**:
   ```json
   {
     "decision": "USE_TOOL",
     "tool_name": "copy_device_credentials",
     "payload": {
       "source_device": "router-01",
       "destination_devices": ["switch-02", "switch-03"]
     }
   }
   ```

3. **Validation**: ✓ Pass (all required fields present, types correct)

4. **Normalization**: 
   - `"router-01"` → `"router-01"` (no change)
   - `["switch-02", "switch-03"]` → `["switch-02", "switch-03"]`

5. **Policy Check**:
   ```json
   {
     "allow": true,
     "reason": "Medium-risk operation allowed for authenticated user"
   }
   ```

6. **Tool Execution**:
   - MCP client calls API tools server
   - API tools server invokes actual NMS API
   - Result: `{"status": "success", "devices_updated": 2}`

7. **Response**:
   ```json
   {
     "decision": "USE_TOOL",
     "tool_used": "copy_device_credentials",
     "message": "Successfully copied credentials from router-01 to 2 devices",
     "api_result": {"status": "success", "devices_updated": 2}
   }
   ```

### Example 2: General Conversation

**User Query**: "Hi"

**Step-by-Step**:

1. **RAG Retrieval**:
   - Query embedding for "Hi"
   - Top-3: `create_ticket`, `list_tickets`, `get_device_credentials` (low similarity < 0.3)

2. **LLM Decision**:
   ```json
   {
     "decision": "GENERAL_RESPONSE",
     "response": "Hello! I'm your NMS API orchestrator assistant. I can help you manage network device credentials, configure SNMP settings, update CLI passwords, and more. What would you like to do today?",
     "notes": "General greeting - no tool lookup needed"
   }
   ```

3. **Response** (short-circuit, no validation/policy/execution):
   ```json
   {
     "decision": "GENERAL_RESPONSE",
     "message": "Hello! I'm your NMS API orchestrator..."
   }
   ```

### Example 3: Missing Information

**User Query**: "Copy credentials"

**Step-by-Step**:

1. **RAG Retrieval**: Top match: `copy_device_credentials`

2. **LLM Decision**:
   ```json
   {
     "decision": "ASK_USER",
     "tool_name": "copy_device_credentials",
     "missing_fields": ["source_device", "destination_devices"],
     "notes": "Need to know which device to copy from and which devices to copy to"
   }
   ```

3. **Response**:
   ```json
   {
     "decision": "ASK_USER",
     "tool_name": "copy_device_credentials",
     "missing_fields": ["source_device", "destination_devices"],
     "message": "I need more information to copy_device_credentials. Please provide: source_device, destination_devices"
   }
   ```

---

## Design Decisions

### 1. Why 7-Step Pipeline?

Each step serves a specific purpose:

| Step | Purpose | Why Needed |
|------|---------|------------|
| RAG | Reduce search space | Can't fit all APIs in LLM prompt |
| LLM | Understand intent | Semantic understanding, parameter extraction |
| Validation | Catch errors early | Prevent invalid API calls |
| Normalization | Data consistency | APIs expect specific formats |
| Policy | Security | Prevent unauthorized/risky operations |
| Execution | Actual work | Invoke real APIs |
| Response | User experience | Human-readable output |

### 2. Why Separate Validation and Normalization?

**Validation first**:
- Ensures structure is correct
- Type checking
- Required fields present

**Then normalization**:
- Applies transformations
- Doesn't change structure
- Safe to apply after validation

**Example**:
```python
# Validation: Check email is string and matches pattern
payload = {"email": "User@Example.COM"}
validate(payload, schema)  # ✓ Pass

# Normalization: Lowercase
payload = normalize(payload)  # {"email": "user@example.com"}
```

### 3. Why OPA for Policy?

**Alternative: Code-based policies**
```python
if tool_name == "delete_device" and not user.is_admin:
    return "denied"
```

**Problems**:
- Scattered across codebase
- Hard to audit
- Difficult to update
- Not reusable

**OPA Benefits**:
- Centralized policy definitions
- Declarative (what, not how)
- Version controlled
- Can be tested independently
- Reusable across services

### 4. Why Embedding Server as Separate Service?

**Alternatives**:
1. **In-process embedding**: Load model in orchestrator
2. **Library call**: Use sentence-transformers directly

**Problems**:
- Large memory footprint (model size)
- Slow startup (model loading)
- Resource contention (CPU/GPU)
- Hard to scale independently

**Separate Server Benefits**:
- Orchestrator stays lightweight
- Can scale embed server independently
- Can upgrade model without redeploying orchestrator
- Multiple services can use same embedder

### 5. Why MCP?

**Without MCP** (Direct API calls):
```python
# Hardcoded in orchestrator
if tool_name == "copy_credentials":
    result = requests.post(
        "https://nms.example.com/api/credentials/copy",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
```

**Problems**:
- Tight coupling
- Hard to test (need real API)
- Difficult to add new tools
- Auth logic scattered
- No retry logic

**With MCP**:
```python
# Clean abstraction
result = await mcp_client.invoke_tool(tool_name, payload)
```

**Benefits**:
- Loose coupling via protocol
- Easy to mock for testing
- Tools are self-describing
- Centralized error handling
- Standardized interface

### 6. Why POC vs. Production Versions?

**POC (docker-compose.poc.yml)**:
- Minimal dependencies
- Fast startup (<2 minutes)
- Ollama (simple LLM)
- No monitoring/tracing
- Good for development/demos

**Production (docker-compose.yml)**:
- Full observability stack
- vLLM (optimized inference)
- Prometheus metrics
- OpenTelemetry tracing
- Grafana dashboards
- Production-ready

---

## Interview Questions & Answers

### Architecture Questions

**Q1: Explain the overall architecture of your system.**

**A**: This is an Agentic RAG system for NMS API orchestration. It uses a 7-step pipeline:
1. RAG retrieves top-K relevant API capabilities using semantic search
2. LLM selects the best tool and extracts parameters from natural language
3. Validation ensures parameters meet JSON schema requirements
4. Normalization standardizes data formats
5. OPA checks security policies
6. MCP executes the actual API call
7. User-friendly response is generated

The system is containerized with 5 services: orchestrator, LLM (Ollama), embed server, API tools, and OPA policy server.

---

**Q2: Why did you choose RAG over fine-tuning?**

**A**: Several reasons:
1. **Dynamic updates**: We can add new APIs without retraining
2. **Cost**: Fine-tuning requires expensive GPU time and large datasets
3. **Accuracy**: RAG retrieves exact API schemas, reducing hallucination
4. **Explainability**: We can see which APIs were retrieved and why
5. **Context length**: Can handle 100s of APIs without hitting token limits

RAG gives us the best of both worlds: LLM's language understanding + exact schema retrieval.

---

**Q3: What happens if RAG retrieves irrelevant capabilities?**

**A**: The LLM acts as a second filter:
1. It analyzes all top-K candidates
2. If none match the user's intent, it returns `decision: "NONE"`
3. User gets a message: "I don't have access to tools for this request"

Example: User asks "What's the weather?" → RAG returns network tools → LLM recognizes mismatch → Returns NONE.

Additionally, we can tune the similarity threshold to filter out low-confidence matches before sending to LLM.

---

### RAG Questions

**Q4: How does the embedding model work?**

**A**: We use `BAAI/bge-small-en-v1.5`:
- **Input**: Text string (e.g., "Copy credentials from router-01")
- **Output**: 384-dimensional vector
- **Process**: Transformer encoder converts text to dense representation
- **Property**: Semantically similar texts have similar vectors

We compute cosine similarity between query vector and capability vectors to find top matches.

---

**Q5: Why top-K=3? Why not 1 or 10?**

**A**: Trade-off between precision and recall:
- **K=1**: Might miss the right tool if similarity scores are close
- **K=3**: Gives LLM options, still manageable context
- **K=10**: Too much context, confuses LLM, increases latency

In practice, top-3 provides ~95% accuracy while keeping prompt size reasonable (~2000 tokens).

---

**Q6: How do you handle updates to the capability registry?**

**A**: Two approaches:
1. **Development**: Modify `capabilities.json`, restart orchestrator (re-computes embeddings at startup)
2. **Production**: Hot reload mechanism:
   - Watch file for changes
   - Re-compute embeddings for new/modified capabilities
   - Update in-memory index without restart

This is a huge advantage of RAG vs. fine-tuning (which requires full retraining).

---

### LLM Questions

**Q7: Why temperature=0.0 for LLM?**

**A**: Tool selection is a **deterministic task**, not creative writing:
- We want the same query to always produce the same tool selection
- Temperature=0 means greedy decoding (always pick highest probability token)
- Ensures consistent JSON formatting
- Reduces risk of invalid responses

For conversational responses (GENERAL_RESPONSE), we could use temperature>0 for more natural language.

---

**Q8: How do you ensure LLM returns valid JSON?**

**A**: Three mechanisms:
1. **Response format**: Set `response_format={"type": "json_object"}` in API call
2. **Prompt engineering**: Explicitly state "respond with ONLY valid JSON"
3. **Fallback**: If JSON parsing fails, retry with stronger prompt or return error

Ollama and vLLM both support constrained generation to enforce JSON schema.

---

**Q9: How do you handle LLM hallucinations?**

**A**: Multiple safeguards:
1. **RAG**: Provides ground truth (actual API schemas)
2. **Validation**: JSON schema validation catches invalid parameters
3. **Tool name check**: Verify LLM-selected tool exists in candidates
4. **Examples**: Provide concrete examples in prompt to guide LLM

If LLM hallucinates a tool name, we catch it in Step 3 and return an error.

---

### MCP Questions

**Q10: What is MCP and why use it?**

**A**: MCP (Model Context Protocol) is a standardized protocol for LLM-tool communication:
- **Standardization**: Common interface for all tools
- **Extensibility**: Easy to add new tools
- **Type safety**: Tools declare input/output schemas
- **Reusability**: Same tools work with different LLMs/agents

Without MCP, we'd have hard-coded API calls in the orchestrator, making it difficult to maintain and extend.

---

**Q11: How does MCP differ from function calling?**

**A**:
- **Function calling**: LLM feature where model decides to call functions
- **MCP**: Protocol for tool execution, separate from LLM

In our system:
- LLM doesn't directly call functions
- LLM returns a decision (which tool + parameters)
- Orchestrator validates, checks policy, then invokes tool via MCP

This separation gives us more control (validation, policy) than direct function calling.

---

### Policy Questions

**Q12: Why use OPA instead of code-based policies?**

**A**: OPA provides:
1. **Declarative policies**: Define what's allowed, not how to check
2. **Centralization**: All policies in one place
3. **Version control**: Policies tracked in Git
4. **Testing**: Can test policies independently
5. **Reusability**: Same policies across multiple services
6. **Auditability**: Easy to review who can do what

Code-based policies scatter logic across codebase and are harder to maintain.

---

**Q13: Give an example of a policy rule.**

**A**:
```rego
# High-risk operations require confirmation
allow if {
    input.risk == "high"
    input.confirmed == true
}
```

This rule checks:
- If operation risk level is "high"
- AND user has confirmed (via UI checkbox/API parameter)
- THEN allow the operation

If `confirmed=false`, OPA returns `allow=false` and orchestrator asks user to confirm.

---

### Performance Questions

**Q14: What's the end-to-end latency?**

**A**: Typical breakdown (POC with Ollama):
1. RAG retrieval: ~50ms (embedding + search)
2. LLM inference: ~500ms (Ollama on CPU)
3. Validation: ~5ms
4. Policy check: ~10ms
5. API execution: ~100ms (depends on external API)

**Total: ~665ms**

With vLLM on GPU, LLM inference drops to ~100ms → **Total: ~265ms**

---

**Q15: How do you scale this system?**

**A**: Three strategies:
1. **Horizontal scaling**: 
   - Run multiple orchestrator instances behind load balancer
   - Stateless design (session ID for multi-turn)

2. **Component scaling**:
   - Scale embed server independently (CPU/GPU)
   - Scale LLM server with vLLM (batching)
   - Scale API tools server based on external API load

3. **Caching**:
   - Cache embeddings (computed once at startup)
   - Cache LLM responses for common queries
   - Cache OPA policy decisions

For 1000s RPS, we'd use vLLM with GPU batching and read replicas for embed server.

---

### Error Handling Questions

**Q16: What happens if the LLM service is down?**

**A**: Health check mechanism:
1. `/health` endpoint checks all services
2. If LLM is down, status = "degraded"
3. New requests return 503 Service Unavailable
4. Existing requests with cached results can still succeed

For production:
- Circuit breaker pattern (stop sending requests after N failures)
- Fallback to rule-based routing (pattern matching)
- Alert on-call team via PagerDuty

---

**Q17: How do you handle invalid user queries?**

**A**: Several cases:
1. **Ambiguous**: LLM returns `ASK_USER` with clarifying questions
2. **Out of domain**: LLM returns `NONE` with helpful message
3. **Malformed**: Input validation catches and returns 400 error
4. **Malicious**: OPA policy blocks, logs security event

Example: "Delete everything" → OPA denies (critical risk without confirmation)

---

### Testing Questions

**Q18: How do you test this system?**

**A**: Multi-level testing:
1. **Unit tests**: Each component (validators, normalizers, etc.)
2. **Integration tests**: 
   - Mock MCP servers
   - Test RAG retrieval accuracy
   - Test LLM prompt engineering
3. **End-to-end tests**: 
   - Real user queries → expected API calls
   - Policy enforcement scenarios
4. **Load tests**: Performance under high RPS

Example test: `tests/test_orchestrate_happy.py` tests the happy path with mocked services.

---

**Q19: How do you evaluate RAG accuracy?**

**A**: Metrics:
1. **Recall@K**: Does top-K contain the correct capability?
2. **MRR (Mean Reciprocal Rank)**: Position of correct capability
3. **End-to-end accuracy**: Does user get correct result?

Process:
1. Create test dataset: 100 queries with known correct tools
2. Run RAG retrieval for each query
3. Measure if correct tool in top-3
4. Target: >95% recall@3

We also do manual review of edge cases and continuously add to test set.

---

### Design Questions

**Q20: Why separate validation and normalization?**

**A**: Separation of concerns:
- **Validation**: Checks correctness (types, required fields, constraints)
- **Normalization**: Transforms data to expected format (lowercase, trim, etc.)

If we normalize first, we might mask validation errors. Example:
- Invalid email: `"user@"` (missing domain)
- If we normalize first (lowercase): `"user@"` → Still invalid
- But error message is less clear

By validating first, we catch structural errors with clear messages, then safely normalize valid data.

---

**Q21: How would you add a new API capability?**

**A**: Simple 3-step process:
1. **Add to registry**: Update `capabilities.json` with schema, examples
2. **Implement tool**: Add tool logic to MCP API tools server
3. **Restart**: Orchestrator re-computes embeddings at startup

No code changes to orchestrator needed! This is a key benefit of the RAG + MCP architecture.

Example:
```json
{
  "name": "backup_device_config",
  "description": "Backup device configuration to remote storage",
  "input_schema": {...},
  "examples": [...]
}
```

---

**Q22: How do you handle multi-turn conversations?**

**A**: Session management:
1. **Session ID**: Unique ID per conversation (UUID)
2. **Context storage**: (Future) Store conversation history in Redis
3. **LLM prompt**: Include previous turns for context

Example:
- Turn 1: "Copy credentials from router-01"
- Bot: "To where?"
- Turn 2: "To switch-02" (same session_id)
- LLM sees both turns → Understands "switch-02" refers to destination

Currently basic (stateless), but architecture supports full context management.

---

### Production Questions

**Q23: What would you change for production?**

**A**: Several enhancements:
1. **LLM**: Swap Ollama → vLLM for better performance
2. **Observability**: 
   - OpenTelemetry tracing (see request flow)
   - Prometheus metrics (latency, error rate)
   - Grafana dashboards
3. **Security**:
   - JWT authentication
   - Rate limiting
   - Input sanitization
4. **Reliability**:
   - Circuit breakers
   - Retry with exponential backoff
   - Graceful degradation
5. **Caching**:
   - Redis for LLM response cache
   - CDN for static content

We have both POC and production docker-compose files to demonstrate this.

---

**Q24: How do you monitor LLM performance?**

**A**: Key metrics:
1. **Latency**: P50, P95, P99 inference time
2. **Accuracy**: % of queries that select correct tool
3. **Token usage**: Prompt + completion tokens (for cost)
4. **Error rate**: JSON parsing failures, invalid tool selections
5. **User satisfaction**: Explicit feedback ("Was this helpful?")

We track these in Prometheus and alert if metrics degrade (e.g., P95 latency > 2s).

---

### NMS-Specific Questions

**Q25: Why focus on network device credentials?**

**A**: Credential management is:
1. **Common**: Every network has 100s-1000s of devices
2. **Tedious**: Manual CLI commands for each device
3. **Error-prone**: Typos can lock admins out
4. **Security-critical**: Wrong credentials = security breach

Natural language interface makes this safer and faster: "Copy credentials from router-01 to all switches in building-A"

---

**Q26: How do you handle device naming ambiguity?**

**A**: Several strategies:
1. **Fuzzy matching**: "router1" matches "router-01"
2. **Context**: If multiple matches, ask user to clarify
3. **Metadata**: Use location, type, IP address to disambiguate
4. **Examples in prompt**: Show LLM how to handle device names

Example:
- User: "Update switch in DC1"
- Multiple matches: [switch-dc1-01, switch-dc1-02, ...]
- Bot: "Which switch in DC1? I found: switch-dc1-01, switch-dc1-02, ..."

---

## Summary

This system demonstrates several advanced concepts:

1. **Agentic RAG**: Combining retrieval with LLM reasoning
2. **MCP**: Standardized tool execution protocol
3. **Policy Enforcement**: OPA for security and authorization
4. **Production-Ready**: Observability, error handling, scaling

**Key Takeaway**: The architecture is modular, each component has a clear responsibility, and the system is designed for extensibility and production use.

---

## Next Steps for Deep Dive

1. **Run the POC**: `docker-compose -f docker-compose.poc.yml up`
2. **Test queries**: Use curl or Postman to send requests
3. **Read the code**: Start with `app_poc.py`, follow the request flow
4. **Modify prompts**: Experiment with different prompt structures
5. **Add a capability**: Try adding a new API to the registry
6. **Review policies**: Understand OPA rules in `policy.rego`

Good luck with your interview! 🚀

