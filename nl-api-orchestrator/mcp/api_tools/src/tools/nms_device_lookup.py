"""
NMS Device Lookup Tool - MCP Tool Implementation.

Resolves device references (brand names, IPs, device types) to actual NMS device_ids.
This tool is called BEFORE credential operations to translate human-readable
device references into the device_identifiers expected by the NMS REST API.

POC: uses in-memory mock data.
Production: replace _lookup_from_nms() with real API call.
"""
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Same mock DB as device_resolver.py (kept in sync) ──────────────────────────
_MOCK_DEVICES: List[Dict[str, Any]] = [
    {"device_id": "SCALANCE-X200-001",  "displayName": "SCALANCE X200 #1",       "ip": "172.16.122.190", "deviceType": "switch",   "category": "industrial_switch",  "brand": "scalance",  "model": "SCALANCE X200",   "location": "Plant Floor A"},
    {"device_id": "SCALANCE-X200-002",  "displayName": "SCALANCE X200 #2",       "ip": "172.16.122.191", "deviceType": "switch",   "category": "industrial_switch",  "brand": "scalance",  "model": "SCALANCE X200",   "location": "Plant Floor B"},
    {"device_id": "SCALANCE-XC200-001", "displayName": "SCALANCE XC200 Core",    "ip": "172.16.122.100", "deviceType": "switch",   "category": "industrial_switch",  "brand": "scalance",  "model": "SCALANCE XC200",  "location": "Server Room"},
    {"device_id": "RUGGEDCOM-RS900-001","displayName": "RUGGEDCOM RS900 #1",     "ip": "172.16.122.200", "deviceType": "switch",   "category": "ruggedized_switch",  "brand": "ruggedcom", "model": "RUGGEDCOM RS900", "location": "Substation A"},
    {"device_id": "RUGGEDCOM-RS900-002","displayName": "RUGGEDCOM RS900 #2",     "ip": "172.16.122.201", "deviceType": "switch",   "category": "ruggedized_switch",  "brand": "ruggedcom", "model": "RUGGEDCOM RS900", "location": "Substation B"},
    {"device_id": "RUGGEDCOM-RS416-001","displayName": "RUGGEDCOM RS416 Gateway","ip": "172.16.122.210", "deviceType": "router",   "category": "ruggedized_router",  "brand": "ruggedcom", "model": "RUGGEDCOM RS416", "location": "Control Room"},
    {"device_id": "FW-SIEMENS-001",     "displayName": "Siemens Firewall #1",    "ip": "10.0.0.1",       "deviceType": "firewall", "category": "firewall",           "brand": "siemens",   "model": "SCALANCE S615",   "location": "DMZ"},
    {"device_id": "RT-CORE-001",        "displayName": "Core Router",            "ip": "192.168.1.1",    "deviceType": "router",   "category": "core_router",        "brand": "cisco",     "model": "ISR 4431",        "location": "Data Center"},
]

_IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
_BRAND_KEYWORDS = ["scalance", "ruggedcom", "siemens", "cisco", "juniper", "aruba", "huawei"]
_TYPE_KEYWORDS  = {
    "switch":   ["switch", "switches", "sw"],
    "router":   ["router", "routers", "rt", "gateway"],
    "firewall": ["firewall", "fw"],
}


def _lookup(reference: str) -> List[Dict[str, Any]]:
    """Lookup a single device reference against the mock DB."""
    ref_lower = reference.strip().lower()
    if not ref_lower:
        return []

    # 1. Exact device_id
    for d in _MOCK_DEVICES:
        if d["device_id"].lower() == ref_lower:
            return [d]

    # 2. IP
    if _IP_RE.match(reference.strip()):
        return [d for d in _MOCK_DEVICES if d["ip"] == reference.strip()]

    # 3. Brand
    for brand in _BRAND_KEYWORDS:
        if brand in ref_lower:
            return [d for d in _MOCK_DEVICES if d["brand"].lower() == brand]

    # 4. Device type
    for dtype, kws in _TYPE_KEYWORDS.items():
        if any(k in ref_lower for k in kws):
            return [d for d in _MOCK_DEVICES if d["deviceType"].lower() == dtype]

    # 5. Partial name
    return [
        d for d in _MOCK_DEVICES
        if ref_lower in d["displayName"].lower() or ref_lower in d["model"].lower()
    ]


async def resolve_device_ids(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Resolve one or more device references (brand names, IPs, device types)
    to NMS device_ids.

    Input:
        references (list[str]) — list of device references to resolve
                                  e.g. ["scalance", "172.16.122.200", "router"]

    Output:
        {
          "status": True,
          "resolved": {
            "scalance": [
              { "device_id": "SCALANCE-X200-001", "displayName": "...", "ip": "...", ... },
              ...
            ],
            "172.16.122.200": [
              { "device_id": "RUGGEDCOM-RS900-001", ... }
            ]
          },
          "unresolved": ["some-unknown-ref"],
          "summary": "Resolved 2/3 references"
        }
    """
    references: List[str] = args.get("references", [])
    if not references:
        return {"status": False, "errorCode": "MISSING_REFERENCES",
                "message": "references list is required"}

    resolved   : Dict[str, List[Dict[str, Any]]] = {}
    unresolved : List[str] = []

    for ref in references:
        matches = _lookup(ref)
        if matches:
            resolved[ref] = matches
            logger.info(f"[resolve] '{ref}' → {[m['device_id'] for m in matches]}")
        else:
            unresolved.append(ref)
            logger.warning(f"[resolve] '{ref}' → no match")

    total   = len(references)
    n_ok    = len(resolved)
    summary = f"Resolved {n_ok}/{total} references"

    return {
        "status": True,
        "errorCode": "SUCCESS",
        "resolved":   resolved,
        "unresolved": unresolved,
        "summary":    summary,
    }

