# Root Cause Analysis: OPA Policy Error

## 🔴 Error Message
```
Policy check failed: Policy check error: 'bool' object has no attribute 'get'
```

## 🔍 Root Cause Analysis

### The Problem
The Python code was trying to call `.get()` method on a boolean value, which caused an `AttributeError`.

### Location of Bug
File: `orchestrator/src/opa_client.py`  
Line: ~72  

```python
# BUGGY CODE:
policy_result = result.get("result", {})  # Assumed this returns a dict
allow = policy_result.get("allow", False)  # ❌ ERROR: policy_result is actually a bool!
```

### Why It Happened

OPA returns **different response formats** depending on which endpoint you query:

#### 1. Query Specific Rule: `/v1/data/policy/allow`
Returns a **boolean** directly:
```json
{
  "result": true
}
```

#### 2. Query Entire Package: `/v1/data/policy`
Returns an **object** with multiple fields:
```json
{
  "result": {
    "allow": true,
    "reason": "Policy evaluation complete"
  }
}
```

### What Went Wrong

1. **Docker-compose** set: `OPA_URL=http://mcp-policy:8181/v1/data/policy/allow`
2. **Code expected**: `result.get("result")` to return `{"allow": true, "reason": "..."}`
3. **OPA actually returned**: `{"result": true}` (boolean, not dict)
4. **Code tried**: `true.get("allow", False)` → **ERROR!** Booleans don't have `.get()` method

### Sequence of Events
```
1. Orchestrator sends policy check request
   └─> POST http://mcp-policy:8181/v1/data/policy/allow
   
2. OPA evaluates policy and returns boolean
   └─> {"result": true}
   
3. Code expects dict but gets bool
   └─> policy_result = true (boolean)
   
4. Code tries: policy_result.get("allow", False)
   └─> AttributeError: 'bool' object has no attribute 'get'
```

## ✅ Solution Applied

### Fix 1: Handle Both Response Formats
Updated `opa_client.py` to handle both boolean and dict responses:

```python
policy_result = result.get("result", {})

# Handle boolean result (when querying /v1/data/policy/allow)
if isinstance(policy_result, bool):
    allow = policy_result
    reason = "Policy evaluation complete"

# Handle object result (when querying /v1/data/policy)
elif isinstance(policy_result, dict):
    allow = policy_result.get("allow", False)
    reason = policy_result.get("reason", "")
else:
    # Unexpected format
    allow = False
    reason = f"Unexpected policy result format"
```

### Fix 2: Change OPA URL to Get More Info
Changed from querying specific rule to querying entire package:

**Before:**
```yaml
OPA_URL=http://mcp-policy:8181/v1/data/policy/allow  # Returns boolean only
```

**After:**
```yaml
OPA_URL=http://mcp-policy:8181/v1/data/policy  # Returns object with allow + reason
```

### Why Query the Package Instead of the Rule?

| Aspect | Query Rule (`/allow`) | Query Package (`/policy`) |
|--------|----------------------|---------------------------|
| URL | `.../v1/data/policy/allow` | `.../v1/data/policy` |
| Returns | Boolean only | Object with multiple fields |
| Info | `true` or `false` | `{allow: true, reason: "..."}` |
| Use Case | Simple yes/no | Detailed decision with reasoning |

## 📊 Files Modified

1. **`orchestrator/src/opa_client.py`**
   - Added type checking for `policy_result`
   - Handle both boolean and dict responses
   - Better error logging

2. **`docker-compose.poc.yml`**
   - Changed: `OPA_URL=http://mcp-policy:8181/v1/data/policy`
   - Removed `/allow` to query entire package

3. **`orchestrator/src/settings.py`**
   - Updated default `opa_url` to match

## 🧪 Testing

### Test 1: Low Risk (Should Allow)
```bash
curl -X POST http://localhost:8181/v1/data/policy \
  -d '{"input": {"risk": "low", "payload": {"description": "test"}}}'
```

**Expected Response:**
```json
{
  "result": {
    "allow": true
  }
}
```

### Test 2: High Risk Without Confirmation (Should Deny)
```bash
curl -X POST http://localhost:8181/v1/data/policy \
  -d '{"input": {"risk": "high", "confirmed": false, "payload": {"description": "dangerous operation"}}}'
```

**Expected Response:**
```json
{
  "result": {
    "allow": false,
    "reason": "High-risk operation requires explicit confirmation"
  }
}
```

## 🎯 Lessons Learned

### 1. **API Response Format Matters**
Always check API documentation for exact response format. OPA's response varies by endpoint.

### 2. **Type Checking is Important**
In Python, always check the type before calling methods:
```python
if isinstance(obj, dict):
    obj.get("key")
elif isinstance(obj, bool):
    # Handle boolean
```

### 3. **Fail-Safe Design**
The fix includes a fallback for unexpected formats:
```python
else:
    logger.warning(f"Unexpected format: {type(policy_result)}")
    allow = False  # Fail-closed for security
```

### 4. **OPA URL Structure**
```
/v1/data/{package}       → Returns all rules in package
/v1/data/{package}/{rule} → Returns single rule value
```

## ✅ Verification Steps

1. **Restart orchestrator:**
   ```bash
   docker-compose -f docker-compose.poc.yml restart orchestrator
   ```

2. **Check logs:**
   ```bash
   docker-compose -f docker-compose.poc.yml logs orchestrator | grep -i "OPA"
   ```
   
   Should show: `Initialized OPAClient with URL: http://mcp-policy:8181/v1/data/policy`

3. **Test policy endpoint directly:**
   ```powershell
   .\verify-opa-fix.ps1
   ```

4. **Test through orchestrator:**
   ```bash
   curl -X POST http://localhost:8080/orchestrate \
     -d '{"query": "list all tickets"}'
   ```

## 📝 Summary

| Issue | Root Cause | Solution |
|-------|------------|----------|
| `'bool' object has no attribute 'get'` | Code expected dict, OPA returned bool | Type checking + query package instead of rule |
| Missing denial reasons | Only got boolean, no reason field | Query `/v1/data/policy` to get full object |
| Code fragility | No type validation | Added `isinstance()` checks for robustness |

**Status:** ✅ **FIXED** - Orchestrator service has been restarted with the updated code.

