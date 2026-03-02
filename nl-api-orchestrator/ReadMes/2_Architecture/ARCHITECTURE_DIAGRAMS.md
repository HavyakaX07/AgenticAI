# 📊 Architecture Diagrams & Visual Reference

## Quick Navigation
1. [System Overview](#system-overview)
2. [Request Flow](#request-flow)
3. [Component Interactions](#component-interactions)
4. [Data Flow](#data-flow)
5. [Deployment Architecture](#deployment-architecture)
6. [Observability Stack](#observability-stack)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER / CLIENT                                  │
│                  Natural Language Query Interface                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTP POST /orchestrate
                                 │ {"query": "Create a ticket for bug"}
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          ORCHESTRATOR SERVICE                            │
│                           (FastAPI - Port 8080)                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Request Processing Pipeline                     │  │
│  │                                                                    │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │  │
│  │  │   Validate   │ ─▶ │  Trace Span  │ ─▶ │   Metrics    │      │  │
│  │  │    Input     │    │   Creation   │    │   Counter    │      │  │
│  │  └──────────────┘    └──────────────┘    └──────────────┘      │  │
│  │                                                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │ STEP 1: RAG - Retrieve Relevant Capabilities                │ │  │
│  │  │  • Query → Embedding (384 dims)                             │ │  │
│  │  │  • Cosine similarity with capability embeddings             │ │  │
│  │  │  • Return top-k (default: 3) capabilities                   │ │  │
│  │  │  • Time: ~100ms                                             │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                            ▼                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │ STEP 2: LLM Reasoning - Decide Action                       │ │  │
│  │  │  • Format prompt with capabilities + query                  │ │  │
│  │  │  • Call LLM (Ollama/vLLM)                                   │ │  │
│  │  │  • Parse JSON response                                      │ │  │
│  │  │  • Validate decision structure                              │ │  │
│  │  │  • Time: ~2000ms                                            │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                            ▼                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │ STEP 3: Policy Check - Authorization                        │ │  │
│  │  │  • Build policy query                                       │ │  │
│  │  │  • Call OPA                                                 │ │  │
│  │  │  • Handle allow/deny                                        │ │  │
│  │  │  • Time: ~50ms                                              │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                            ▼                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │ STEP 4: Tool Execution - MCP Call                           │ │  │
│  │  │  • Validate tool exists                                     │ │  │
│  │  │  • Validate arguments                                       │ │  │
│  │  │  • Execute via MCP                                          │ │  │
│  │  │  • Parse response                                           │ │  │
│  │  │  • Time: ~500ms                                             │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                            ▼                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │ STEP 5: Response Formation                                  │ │  │
│  │  │  • Normalize result                                         │ │  │
│  │  │  • Add metadata (session_id, timestamps)                    │ │  │
│  │  │  • Log completion                                           │ │  │
│  │  │  • Return to user                                           │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────┬──────────────┬──────────────┬──────────────┬─────────────┘
              │              │              │              │
              ▼              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   OLLAMA     │ │  MCP-EMBED   │ │   MCP-API    │ │ MCP-POLICY   │
    │    (LLM)     │ │ (Embeddings) │ │   (Tools)    │ │    (OPA)     │
    │  Port 11434  │ │  Port 9001   │ │  Port 9000   │ │  Port 8181   │
    └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Request Flow (Sequence Diagram)

```
User        Orchestrator    Retriever    LLM(Ollama)    OPA      MCP-API    External-API
 │               │              │             │          │           │            │
 │─Create ticket─▶              │             │          │           │            │
 │               │              │             │          │           │            │
 │               │─retrieve()──▶│             │          │           │            │
 │               │              │─embed()────▶│          │           │            │
 │               │              │◀────────────│          │           │            │
 │               │              │             │          │           │            │
 │               │              │[similarity] │          │           │            │
 │               │◀─[top-3]─────│             │          │           │            │
 │               │              │             │          │           │            │
 │               │──────format prompt────────▶│          │           │            │
 │               │                             │          │           │            │
 │               │                    [LLM inference]     │           │            │
 │               │                             │          │           │            │
 │               │◀──{decision, tool, args}────│          │           │            │
 │               │                             │          │           │            │
 │               │──────check_policy()────────────────▶   │           │            │
 │               │◀───────{allow: true}────────────────   │           │            │
 │               │                             │          │           │            │
 │               │──────call_tool()───────────────────────────▶       │            │
 │               │                             │          │           │            │
 │               │                             │          │           │─POST /api─▶│
 │               │                             │          │           │◀───200─────│
 │               │                             │          │           │            │
 │               │◀──────{result}──────────────────────────────────   │            │
 │               │                             │          │           │            │
 │◀──response────│                             │          │           │            │
 │               │                             │          │           │            │

Timeline:
├─ 0ms:    Request received
├─ 10ms:   Validation complete
├─ 110ms:  RAG retrieval complete  (100ms)
├─ 2110ms: LLM reasoning complete  (2000ms)
├─ 2160ms: Policy check complete   (50ms)
├─ 2660ms: Tool execution complete (500ms)
└─ 2670ms: Response sent           (10ms)

Total: ~2.7 seconds
```

---

## Component Interactions (Detailed)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR COMPONENTS                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                     retriever.py                                │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │  CapabilityRetriever                                      │  │   │
│  │  │  • initialize() → load capabilities, compute embeddings  │  │   │
│  │  │  • retrieve(query, top_k) → semantic search             │  │   │
│  │  │  • _embed_single(text) → call embedding service         │  │   │
│  │  │  • _cosine_similarity() → rank capabilities             │  │   │
│  │  └──────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────┬──────────────────────────────────────────┘   │
│                        │ uses                                          │
│                        ▼                                               │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                   mcp_client.py                                 │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │  MCPClient                                                │  │   │
│  │  │  • list_tools() → discover available tools              │  │   │
│  │  │  • call_tool(name, args) → execute tool                 │  │   │
│  │  │  • _validate_arguments() → JSON schema validation       │  │   │
│  │  └──────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────┬──────────────────────────────────────────┘   │
│                        │ uses                                          │
│                        ▼                                               │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                   opa_client.py                                 │   │
│  │  ┌──────────────────────────────────────────────────────────┐  │   │
│  │  │  OPAClient                                                │  │   │
│  │  │  • check_policy(action, user, params) → bool            │  │   │
│  │  │  • _build_query() → format OPA request                  │  │   │
│  │  └──────────────────────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                    prompts.py                                   │   │
│  │  • ORCHESTRATION_PROMPT → LLM instruction template            │   │
│  │  • _format_capabilities() → convert to LLM-readable format    │   │
│  │  • _extract_json_from_markdown() → parse LLM response         │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                   validators.py                                 │   │
│  │  • validate_url(url, allowlist) → security check              │   │
│  │  • validate_payload(data, schema) → input validation          │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                   settings.py                                   │   │
│  │  • Settings (Pydantic BaseSettings)                            │   │
│  │  • Load from .env file                                         │   │
│  │  • Provide defaults                                            │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow (RAG Pipeline)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    INDEXING PHASE (Startup)                          │
└─────────────────────────────────────────────────────────────────────┘

registry/capabilities.json
         │
         │ Load
         ▼
┌─────────────────────┐
│  Capability Cards   │
│  [{                 │
│    name: "...",     │
│    description: "", │
│    examples: []     │
│  }]                 │
└──────────┬──────────┘
           │
           │ For each capability
           ▼
┌──────────────────────────────┐
│  Create Text Representation  │
│  "Name: create_ticket |      │
│   Description: ... |         │
│   Examples: ..."             │
└──────────┬───────────────────┘
           │
           │ Batch embed
           ▼
┌──────────────────────────────┐
│    MCP-Embed Service         │
│    POST /embed               │
│    {"texts": [...]}          │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Embeddings Matrix           │
│  [[0.23, -0.45, ...],       │
│   [0.67, 0.12, ...],        │
│   [-0.34, 0.89, ...]]       │
│  Shape: (N, 384)             │
└──────────┬───────────────────┘
           │
           │ Cache in memory
           ▼
┌──────────────────────────────┐
│  Ready for retrieval!        │
└──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   RETRIEVAL PHASE (Per Request)                      │
└─────────────────────────────────────────────────────────────────────┘

User Query: "Create a ticket for login bug"
     │
     │ Embed
     ▼
┌──────────────────────────────┐
│  Query Embedding             │
│  [0.45, -0.23, 0.78, ...]   │
│  Shape: (384,)               │
└──────────┬───────────────────┘
           │
           │ Compute similarity
           ▼
┌──────────────────────────────────────────────┐
│  Cosine Similarity                           │
│  query_emb · capability_emb                  │
│  ──────────────────────────────              │
│  ||query_emb|| × ||capability_emb||          │
│                                              │
│  Results:                                    │
│  [0.92, 0.78, 0.45, 0.23, ...]              │
└──────────┬───────────────────────────────────┘
           │
           │ Sort & select top-k
           ▼
┌──────────────────────────────────────────────┐
│  Top-3 Capabilities                          │
│  1. create_ticket     (score: 0.92)         │
│  2. update_ticket     (score: 0.78)         │
│  3. list_tickets      (score: 0.45)         │
└──────────┬───────────────────────────────────┘
           │
           │ Send to LLM
           ▼
    [LLM Reasoning]
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Host                                  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    nl-api-net (Bridge Network)              │   │
│  │                                                             │   │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │   │
│  │  │ orchestrator │   │   ollama     │   │  mcp-embed   │  │   │
│  │  │              │   │              │   │              │  │   │
│  │  │ Port: 8080   │   │ Port: 11434  │   │ Port: 9001   │  │   │
│  │  │              │   │              │   │              │  │   │
│  │  │ Volume:      │   │ Volume:      │   │ Volume:      │  │   │
│  │  │ ./src        │   │ ollama-data  │   │ embed-cache  │  │   │
│  │  └──────────────┘   └──────────────┘   └──────────────┘  │   │
│  │                                                             │   │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │   │
│  │  │  mcp-api     │   │ mcp-policy   │   │   traefik    │  │   │
│  │  │              │   │     (OPA)    │   │  (Gateway)   │  │   │
│  │  │ Port: 9000   │   │ Port: 8181   │   │ Port: 80     │  │   │
│  │  │              │   │              │   │ Port: 8090   │  │   │
│  │  │ Volume:      │   │ Volume:      │   │              │  │   │
│  │  │ ./tools      │   │ ./policy     │   │              │  │   │
│  │  └──────────────┘   └──────────────┘   └──────────────┘  │   │
│  │                                                             │   │
│  │  ┌──────────────────────────────────────────────────────┐ │   │
│  │  │          OBSERVABILITY STACK                         │ │   │
│  │  │                                                       │ │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │ │   │
│  │  │  │ otelcol  │  │  jaeger  │  │  loki    │          │ │   │
│  │  │  │ :4317    │  │ :16686   │  │ :3100    │          │ │   │
│  │  │  └──────────┘  └──────────┘  └──────────┘          │ │   │
│  │  │                                                       │ │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │ │   │
│  │  │  │prometheus│  │ grafana  │  │ promtail │          │ │   │
│  │  │  │ :9090    │  │ :3000    │  │          │          │ │   │
│  │  │  └──────────┘  └──────────┘  └──────────┘          │ │   │
│  │  └───────────────────────────────────────────────────────┘ │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Volumes:                                                           │
│  • ollama-data      → Model weights (GBs)                          │
│  • embed-cache      → Embedding model cache                        │
│  • prometheus-data  → Metrics time-series                          │
│  • grafana-data     → Dashboard configs                            │
│  • loki-data        → Log storage                                  │
└─────────────────────────────────────────────────────────────────────┘

Exposed Ports:
• 8080  → Orchestrator API
• 11434 → Ollama API (for debugging)
• 3000  → Grafana dashboards
• 9090  → Prometheus UI
• 16686 → Jaeger traces
```

---

## Observability Stack (Data Flow)

```
┌────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                           │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ orchestrator │  │  mcp-embed   │  │   mcp-api    │            │
│  │              │  │              │  │              │            │
│  │ • Traces     │  │ • Traces     │  │ • Traces     │            │
│  │ • Metrics    │  │ • Metrics    │  │ • Metrics    │            │
│  │ • Logs       │  │ • Logs       │  │ • Logs       │            │
│  └─────┬────────┘  └─────┬────────┘  └─────┬────────┘            │
│        │                  │                  │                     │
└────────┼──────────────────┼──────────────────┼─────────────────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
                ▼           ▼           ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ TRACES   │  │ METRICS  │  │   LOGS   │
        │          │  │          │  │          │
        │ OpenTel  │  │Prometheus│  │ Promtail │
        │ Collector│  │  :9090   │  │          │
        │  :4317   │  │          │  │          │
        └────┬─────┘  └────┬─────┘  └────┬─────┘
             │             │             │
             ▼             │             ▼
        ┌──────────┐       │        ┌──────────┐
        │  Jaeger  │       │        │   Loki   │
        │  :16686  │       │        │  :3100   │
        │          │       │        │          │
        │ [Traces] │       │        │  [Logs]  │
        └────┬─────┘       │        └────┬─────┘
             │             │             │
             └─────────────┼─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   GRAFANA    │
                    │    :3000     │
                    │              │
                    │ • Dashboards │
                    │ • Alerts     │
                    │ • Query UI   │
                    └──────────────┘

Data Types:

TRACES (OpenTelemetry):
• Span: orchestrate_request
  ├─ Span: retrieve_capabilities (100ms)
  ├─ Span: llm_reasoning (2000ms)
  ├─ Span: policy_check (50ms)
  └─ Span: execute_tool (500ms)

METRICS (Prometheus):
• orchestrator_requests_total{decision="USE_TOOL"}
• orchestrator_request_duration_seconds{quantile="0.95"}
• llm_tokens_total{type="input"}

LOGS (Structured JSON):
{
  "timestamp": "2026-02-12T20:00:00Z",
  "level": "INFO",
  "message": "orchestration_complete",
  "query": "Create ticket",
  "decision": "USE_TOOL",
  "duration_ms": 2650
}
```

---

## Production Scaling Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LOAD BALANCER                                │
│                         (nginx/traefik)                              │
└────────────┬────────────────────────────────────────────────────────┘
             │
             │ Round-robin
             │
   ┌─────────┼─────────┬─────────┬─────────┐
   │         │         │         │         │
   ▼         ▼         ▼         ▼         ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│Orch 1│ │Orch 2│ │Orch 3│ │Orch 4│ │Orch 5│
│      │ │      │ │      │ │      │ │      │
└───┬──┘ └───┬──┘ └───┬──┘ └───┬──┘ └───┬──┘
    │        │        │        │        │
    └────────┴────────┴────────┴────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │ Redis  │  │Vector  │  │  OPA   │
    │(Cache) │  │  DB    │  │Cluster │
    └────────┘  └────────┘  └────────┘
         │           │           │
         └───────────┼───────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │ LLM    │  │ MCP    │  │  MCP   │
    │Pool    │  │ Embed  │  │  API   │
    │(vLLM)  │  │Cluster │  │Cluster │
    └────────┘  └────────┘  └────────┘

Key Scaling Strategies:
1. Horizontal: Multiple orchestrator instances
2. Caching: Redis for LLM responses & embeddings
3. Vector DB: Pinecone/Weaviate for fast retrieval
4. LLM Pool: vLLM with request batching
5. Service Mesh: Istio for traffic management
```

---

## Interview Whiteboard Template

**Use this for interviews - practice drawing it!**

```
Simple 3-Box Diagram:

┌─────────────┐
│    USER     │
└──────┬──────┘
       │ "Create ticket"
       ▼
┌─────────────────────────┐
│    ORCHESTRATOR         │
│                         │
│  RAG → LLM → Policy     │
│   ↓     ↓      ↓        │
└──────────┬──────────────┘
           │
           ▼
   ┌───────────────┐
   │  MCP SERVERS  │
   │ (Tools/APIs)  │
   └───────────────┘

Then expand each box as needed based on questions!
```

---

## Component Responsibility Matrix

```
┌──────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│ Component    │ Input       │ Process     │ Output      │ Purpose     │
├──────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Orchestrator │ NL query    │ Coordinate  │ Result      │ Main brain  │
│              │             │ pipeline    │ + message   │             │
├──────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Retriever    │ Query text  │ Embed +     │ Top-k caps  │ Find        │
│              │             │ similarity  │             │ relevant    │
├──────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ LLM          │ Prompt +    │ Inference   │ JSON        │ Decide      │
│ (Ollama)     │ capabilities│             │ decision    │ action      │
├──────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ OPA          │ Policy      │ Evaluate    │ Allow/      │ Authorize   │
│              │ query       │ rules       │ Deny        │             │
├──────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ MCP Client   │ Tool name + │ Validate +  │ Tool result │ Execute     │
│              │ arguments   │ call server │             │ tools       │
├──────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ MCP Server   │ MCP request │ Execute     │ MCP         │ Provide     │
│              │             │ tool logic  │ response    │ tools       │
├──────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Embed        │ Text        │ Encode to   │ Vector      │ Enable      │
│ Service      │             │ vector      │ (384 dims)  │ RAG         │
└──────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

---

## Key Metrics Dashboard Layout

```
┌────────────────────────────────────────────────────────────────────┐
│  NL → API Orchestrator Dashboard                          [Grafana]│
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────┐              │
│  │  Request Rate        │  │  Error Rate          │              │
│  │  ▁▂▃▄▅▆▇█            │  │  ▁▁▁▂▁▁▁▁            │              │
│  │  125 req/sec         │  │  0.8%                │              │
│  └──────────────────────┘  └──────────────────────┘              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Latency Percentiles                                         │ │
│  │  p50: 2.1s  ██████████░░░░░░░░░░                            │ │
│  │  p95: 3.8s  █████████████████░░░░                           │ │
│  │  p99: 5.2s  ███████████████████░░                           │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌────────────────────┐  ┌────────────────────┐                  │
│  │ Decision Types     │  │  LLM Token Usage   │                  │
│  │ USE_TOOL:   65%    │  │  ▁▃▅▇█▇▅▃▁         │                  │
│  │ ASK_USER:   25%    │  │  15k tokens/min    │                  │
│  │ NONE:       10%    │  │                    │                  │
│  └────────────────────┘  └────────────────────┘                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Component Latency Breakdown                                 │ │
│  │  RAG:        100ms  █                                        │ │
│  │  LLM:       2000ms  ████████████████████                     │ │
│  │  Policy:      50ms  ░                                        │ │
│  │  Tool:       500ms  █████                                    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Technology Decision Tree

```
Choosing LLM Provider:

Start
  │
  ├─ Need latest/best quality?
  │  └─ Yes → GPT-4 (OpenAI)
  │  └─ No ↓
  │
  ├─ Privacy critical?
  │  └─ Yes → Local (Ollama/vLLM)
  │  └─ No ↓
  │
  ├─ High throughput needed?
  │  └─ Yes → vLLM (optimized)
  │  └─ No ↓
  │
  ├─ Easy management preferred?
  │  └─ Yes → Ollama ✅ (our choice)
  │  └─ No → vLLM
  

Choosing Vector Store:

Start
  │
  ├─ <1000 documents?
  │  └─ Yes → In-memory ✅ (our choice)
  │  └─ No ↓
  │
  ├─ Need filtering/metadata?
  │  └─ Yes → Weaviate
  │  └─ No ↓
  │
  ├─ Managed service OK?
  │  └─ Yes → Pinecone
  │  └─ No → Qdrant (self-hosted)
```

---

## Summary: What to Remember

**For 30-second explanation**: Draw the 3-box diagram (User → Orchestrator → MCP)

**For 2-minute explanation**: Show full system overview with 5 steps

**For 5-minute explanation**: Walk through sequence diagram with timing

**For technical discussion**: Show component interactions and code structure

**For scaling discussion**: Show production architecture with load balancer

**For observability**: Show the three pillars (traces, metrics, logs)

---

## Practice Exercise

**Task**: Draw this system from memory in 5 minutes

**Checklist**:
- [ ] User at top
- [ ] Orchestrator in middle with 4-5 steps
- [ ] Supporting services at bottom (Ollama, MCP servers)
- [ ] Arrows showing data flow
- [ ] Rough timing estimates
- [ ] Key technologies labeled

**Tip**: Don't aim for perfection - aim for clear communication!

Good luck! 🎯

