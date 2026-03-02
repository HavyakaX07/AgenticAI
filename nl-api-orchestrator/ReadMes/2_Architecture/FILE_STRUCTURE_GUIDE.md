# 📁 File Structure Guide - POC vs Production

This document explains which files are **REQUIRED** for the POC and which are **OPTIONAL** (for production/development only).

## ✅ REQUIRED Files for POC

### Root Directory
```
✅ docker-compose.poc.yml          # POC docker compose configuration
✅ start-poc.ps1                   # POC startup script (Windows)
✅ README_POC.md                   # POC documentation
❌ docker-compose.yml              # PRODUCTION - Full stack with monitoring
❌ start.ps1/start.sh              # PRODUCTION - Full stack startup
❌ test.ps1/test.sh                # DEVELOPMENT - Testing scripts
❌ setup-ollama.ps1                # OPTIONAL - Ollama setup helper
```

### Orchestrator (Core Service)
```
orchestrator/
  ✅ Dockerfile.poc                # POC dockerfile
  ✅ requirements.poc.txt          # Minimal dependencies
  ❌ Dockerfile                    # PRODUCTION - with monitoring
  ❌ requirements.txt              # PRODUCTION - full dependencies
  
  src/
    ✅ app_poc.py                  # POC app without monitoring
    ✅ settings.py                 # Configuration
    ✅ retriever.py                # RAG capability retriever
    ✅ tool_router.py              # LLM tool selection
    ✅ mcp_client.py               # MCP protocol client
    ✅ opa_client.py               # OPA policy client
    ✅ validators.py               # Payload validation
    ✅ normalizers.py              # Data normalization
    ✅ prompts.py                  # LLM prompts
    ❌ app.py                      # PRODUCTION - with monitoring
    ❌ logging_conf.py             # PRODUCTION - advanced logging
  
  registry/
    ✅ capabilities.json           # API capability definitions
  
  tests/
    ❌ *                           # DEVELOPMENT - Not needed for POC
```

### MCP Embed Tools (RAG Embeddings)
```
mcp/embed_tools/
  ✅ Dockerfile.poc                # POC dockerfile
  ✅ requirements.poc.txt          # Minimal dependencies
  ❌ Dockerfile                    # PRODUCTION
  ❌ requirements.txt              # PRODUCTION
  
  src/
    ✅ server.py                   # Embedding server
```

### MCP API Tools (Tool Execution)
```
mcp/api_tools/
  ✅ Dockerfile.poc                # POC dockerfile
  ✅ requirements.poc.txt          # Minimal dependencies
  ❌ Dockerfile                    # PRODUCTION
  ❌ requirements.txt              # PRODUCTION
  
  src/
    ✅ server.py                   # API tools server
    tools/
      ✅ __init__.py               # Package init
      ✅ create_ticket.py          # Example tool
      ✅ list_tickets.py           # Example tool
```

### OPA Policy (Security)
```
mcp/policy/
  ✅ policy.rego                   # Security policy rules
  ⚠️  Uses official OPA image (no custom build needed)
```

### Monitoring & Observability (NOT NEEDED FOR POC)
```
❌ ops/                            # PRODUCTION ONLY
   ❌ prometheus.yml               # Metrics collection
   ❌ loki-config.yaml             # Log aggregation
   ❌ promtail-config.yml          # Log shipping
   ❌ otelcol-config.yaml          # Tracing collector
   ❌ grafana-provisioning/        # Dashboard definitions

❌ gateway/                        # PRODUCTION ONLY
   ❌ traefik.yml                  # API gateway config
```

### Documentation (OPTIONAL - for learning)
```
⚠️  README.md                      # Main documentation
⚠️  ARCHITECTURE.md                # System architecture
⚠️  INTERVIEW_GUIDE.md             # Interview preparation
⚠️  TECHNICAL_DEEP_DIVE.md         # Technical details
⚠️  MIGRATION_TO_OLLAMA.md         # Migration guide
⚠️  CONTRIBUTING.md                # Contribution guide
⚠️  LICENSE                        # License file
```

## 📊 Dependency Comparison

### orchestrator/requirements.poc.txt (POC)
```python
# TOTAL: 8 packages (~50MB)
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0
httpx==0.26.0
openai==1.10.0
jsonschema==4.21.0
python-json-logger==2.0.7
```

### orchestrator/requirements.txt (Production)
```python
# TOTAL: 17 packages (~500MB)
# Above packages PLUS:
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-instrumentation-fastapi==0.43b0
opentelemetry-exporter-otlp==1.22.0
prometheus-client==0.19.0
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
pytest-mock==3.12.0
```

## 🎯 What Each Service Does

### Required for POC

| Service | Purpose | Image Size | Required? |
|---------|---------|------------|-----------|
| **orchestrator** | Main brain - handles queries | ~500MB | ✅ YES |
| **ollama** | LLM inference | ~4.7GB* | ✅ YES |
| **mcp-embed** | RAG embeddings | ~800MB | ✅ YES |
| **mcp-api** | Tool execution | ~300MB | ✅ YES |
| **opa** | Policy enforcement | ~50MB | ✅ YES |

*Includes llama3.1:8b model

### Not Needed for POC

| Service | Purpose | Image Size | Required? |
|---------|---------|------------|-----------|
| traefik | API gateway | ~100MB | ❌ NO |
| otelcol | Trace collection | ~200MB | ❌ NO |
| jaeger | Trace visualization | ~100MB | ❌ NO |
| prometheus | Metrics storage | ~200MB | ❌ NO |
| grafana | Dashboards | ~300MB | ❌ NO |
| loki | Log aggregation | ~100MB | ❌ NO |
| promtail | Log shipping | ~100MB | ❌ NO |

## 🚀 Quick Reference

### To Run POC:
```bash
# All you need:
docker compose -f docker-compose.poc.yml up -d
```

### To Run Full Production:
```bash
# Uses all monitoring services:
docker compose -f docker-compose.yml up -d
```

## 📦 What Gets Built

### POC Build
```
Building:
  1. orchestrator (POC) - ~2 minutes
  2. mcp-embed (POC)    - ~3 minutes
  3. mcp-api (POC)      - ~1 minute

Pulling:
  4. ollama             - Pre-built image
  5. opa                - Pre-built image

Total Build Time: ~6 minutes (first time)
Total Image Size: ~6GB
```

### Production Build
```
Building:
  1. orchestrator (Full) - ~4 minutes
  2. mcp-embed (Full)    - ~3 minutes
  3. mcp-api (Full)      - ~1 minute

Pulling:
  4. ollama              - Pre-built image
  5. opa                 - Pre-built image
  6. traefik             - Pre-built image
  7. otelcol             - Pre-built image
  8. jaeger              - Pre-built image
  9. prometheus          - Pre-built image
  10. grafana            - Pre-built image
  11. loki               - Pre-built image
  12. promtail           - Pre-built image

Total Build Time: ~8 minutes (first time)
Total Image Size: ~12GB
```

## 🔍 Code Differences

### app_poc.py vs app.py

**app_poc.py** (POC)
```python
# ✅ Included
- FastAPI app
- Request/response models
- Health checks
- Main orchestration logic
- Logging (basic)

# ❌ Removed
- OpenTelemetry tracing
- Prometheus metrics
- Distributed spans
- Metric counters/histograms
```

**app.py** (Production)
```python
# ✅ Everything in POC PLUS:
- OpenTelemetry instrumentation
- Prometheus metrics endpoint
- Request tracing with spans
- Performance metrics
- Token usage tracking
```

## 💡 Minimal POC Checklist

To run the absolute minimum POC, you only need:

- [ ] `docker-compose.poc.yml`
- [ ] `start-poc.ps1` (optional, can run docker command directly)
- [ ] `orchestrator/` (with POC files)
- [ ] `mcp/embed_tools/` (with POC files)
- [ ] `mcp/api_tools/` (with POC files)
- [ ] `mcp/policy/policy.rego`

**That's it! Everything else is optional.**

## 🎓 When to Use What

### Use POC When:
- ✅ Demonstrating the concept
- ✅ Learning the system
- ✅ Quick testing
- ✅ Resource-constrained environment
- ✅ Interview presentations

### Use Production When:
- ✅ Production deployment
- ✅ Performance analysis needed
- ✅ Debugging complex issues
- ✅ Long-term monitoring
- ✅ Multi-user environment

## 📝 Comments in Original Files

I've added comments to the original `docker-compose.yml` indicating which services are optional:

```yaml
# OPTIONAL FOR POC - Can be commented out:
# - traefik
# - otelcol
# - jaeger
# - prometheus
# - grafana
# - loki
# - promtail
```

---

**Summary**: For POC, you need 5 services. For production, you get 12 services with full observability.

