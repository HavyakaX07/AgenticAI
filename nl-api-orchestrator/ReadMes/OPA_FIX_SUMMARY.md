# OPA Policy Issue - Resolution Summary

## Problem Identified
The orchestrator was trying to connect to `http://mcp-policy:8181` (missing the policy endpoint path), resulting in a **404 Not Found** error when checking policies.

## Root Cause
In `docker-compose.poc.yml`, the environment variable was set incorrectly:
```yaml
- OPA_URL=http://mcp-policy:8181  # ❌ WRONG - missing path
```

OPA requires the full path to the policy evaluation endpoint:
```
http://mcp-policy:8181/v1/data/{package}/{rule}
```

## Solution Applied

### 1. Fixed docker-compose.poc.yml
Changed line 36 from:
```yaml
- OPA_URL=http://mcp-policy:8181
```
To:
```yaml
- OPA_URL=http://mcp-policy:8181/v1/data/policy/allow
```

### 2. Enhanced opa_client.py
- Added URL validation to warn if `/v1/data/` is missing
- Improved error logging to show the actual URL being called
- Better error handling for HTTP status errors

## How to Verify the Fix

### 1. Restart the services:
```powershell
cd D:\AgenticAI\AgenticRAGWithMCP\nl-api-orchestrator
docker-compose -f docker-compose.poc.yml down
docker-compose -f docker-compose.poc.yml up -d
```

### 2. Check orchestrator logs:
```powershell
docker-compose -f docker-compose.poc.yml logs orchestrator | Select-String -Pattern "OPA"
```

You should see:
```
INFO - OPA: http://mcp-policy:8181/v1/data/policy/allow
INFO - Initialized OPAClient with URL: http://mcp-policy:8181/v1/data/policy/allow
INFO - ✓ OPA Client initialized
```

### 3. Test the policy endpoint directly:
```powershell
# Test low-risk operation (should allow)
Invoke-RestMethod -Uri "http://localhost:8181/v1/data/policy/allow" `
  -Method Post `
  -Body '{"input": {"risk": "low", "payload": {"description": "test"}}}' `
  -ContentType "application/json"
```

Expected response:
```json
{
  "result": {
    "allow": true
  }
}
```

### 4. Test through the orchestrator:
```powershell
# Make a request to the orchestrator that will trigger policy check
Invoke-RestMethod -Uri "http://localhost:8080/orchestrate" `
  -Method Post `
  -Body '{"query": "list all tickets"}' `
  -ContentType "application/json"
```

### 5. Check container health:
```powershell
docker-compose -f docker-compose.poc.yml ps
```

All containers should show status: `Up XX seconds (healthy)`

## Understanding OPA URLs

### OPA URL Structure:
```
http://{host}:{port}/v1/data/{package_path}/{rule_name}
```

Examples:
- `http://mcp-policy:8181/v1/data/policy/allow` - Policy package "policy", rule "allow"
- `http://mcp-policy:8181/v1/data/api/authz/allow` - Package "api.authz", rule "allow"

### Health Check URL:
```
http://mcp-policy:8181/health
```
This is a different endpoint used only for Docker health checks.

## Why the Container Shows "Healthy" But Gave 404

The Docker health check uses `/health` endpoint:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8181/health?bundle=true"]
```

This endpoint always returns 200 OK if OPA is running, **regardless of whether policies are loaded correctly**.

The `/v1/data/policy/allow` endpoint is the actual policy evaluation endpoint, which requires:
1. OPA server to be running ✅
2. Policy files to be loaded from `/policies` volume ✅
3. Correct URL path to match the package/rule name ❌ (This was the issue)

## Files Modified
1. `docker-compose.poc.yml` - Fixed OPA_URL environment variable
2. `orchestrator/src/opa_client.py` - Enhanced error handling and logging

## Next Steps
Once containers are fully started (wait 30-60 seconds), test the orchestrator with a sample query to ensure end-to-end functionality works correctly.

