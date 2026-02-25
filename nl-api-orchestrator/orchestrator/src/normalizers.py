"""
Payload normalization utilities for NMS Credential Management.
Normalizes device identifiers, SNMP versions, credential types, ports, and
other fields based on the validation_rules and context_enrichment sections of
credential_api_nlp_metadata.json.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ── Credential type normalisation (from nlp_metadata entity_extraction.credential_type.mappings)
CREDENTIAL_TYPE_MAP: Dict[str, str] = {
    "snmp":     "snmp_read",
    "community":"snmp_read",
    "snmpread": "snmp_read",
    "snmp_r":   "snmp_read",
    "snmpwrite":"snmp_write",
    "snmp_w":   "snmp_write",
    "ssh":      "cli",
    "telnet":   "cli",
    "shell":    "cli",
    "console":  "cli",
    "https":    "cli",
    "http":     "cli",
    "netconf":  "cli",
}

# ── SNMP version normalisation (from entity_extraction.snmp_version.mappings)
SNMP_VERSION_MAP: Dict[str, int] = {
    "v1":  1, "version1": 1, "1": 1,
    "v2":  2, "version2": 2, "2": 2, "v2c": 2,
    "v3":  3, "version3": 3, "3": 3,
}

# ── Default port values (from validation_rules defaults)
DEFAULT_SNMP_PORT    = 161
DEFAULT_SSH_PORT     = 22
DEFAULT_NETCONF_PORT = 830
DEFAULT_HTTPS_PORT   = 443
DEFAULT_RETRIES      = 3
DEFAULT_TIMEOUT      = 5
DEFAULT_RETRY_TIMEOUT = 30

# ── Action synonym normalisation (from context_enrichment.action_synonyms)
# Maps user variants to canonical API boolean flag names
CREDENTIAL_FLAG_ALIASES: Dict[str, str] = {
    "snmp_read":   "snmpRead",
    "snmp_write":  "snmpWrite",
    "snmpread":    "snmpRead",
    "snmpwrite":   "snmpWrite",
    "snmp read":   "snmpRead",
    "snmp write":  "snmpWrite",
    "cli":         "cli",
    "ssh":         "cli",
    "telnet":      "cli",
}


# ── Utility helpers ─────────────────────────────────────────────────────────────

def _normalize_device_id(value: Any) -> Any:
    """Trim whitespace from a device identifier string."""
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_device_ids(value: Any) -> Any:
    """
    Ensure device IDs is a list of trimmed strings.
    Accepts: list | comma-separated string | single string
    """
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        # Split on comma or semicolon
        parts = [p.strip() for p in value.replace(";", ",").split(",") if p.strip()]
        return parts if len(parts) > 1 else (parts[0] if parts else value.strip())
    return value


def _normalize_snmp_version(value: Any) -> Any:
    """Normalise SNMP version to integer 1, 2, or 3."""
    if isinstance(value, int) and value in (1, 2, 3):
        return value
    if isinstance(value, str):
        key = value.lower().strip().replace(" ", "")
        if key in SNMP_VERSION_MAP:
            return SNMP_VERSION_MAP[key]
    return value


def _apply_snmp_defaults(cred_block: Dict[str, Any], is_write: bool = False) -> Dict[str, Any]:
    """
    Apply default values for SNMP credential blocks as defined in
    validation_rules.snmp_read / snmp_write default_values.
    """
    result = cred_block.copy()
    result.setdefault("port",    DEFAULT_SNMP_PORT)
    result.setdefault("retries", DEFAULT_RETRIES)
    if not is_write:
        result.setdefault("timeout", DEFAULT_TIMEOUT)
    return result


def _apply_cli_defaults(cred_block: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply default values for CLI credential blocks as defined in
    validation_rules.cli.default_values.
    """
    result = cred_block.copy()
    result.setdefault("sshPort",     DEFAULT_SSH_PORT)
    result.setdefault("netconfPort", DEFAULT_NETCONF_PORT)
    result.setdefault("httpsPort",   DEFAULT_HTTPS_PORT)
    result.setdefault("retryTimeout",DEFAULT_RETRY_TIMEOUT)
    return result


# ── Per-tool normalisation rules ────────────────────────────────────────────────

def _normalize_copy_credentials(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise copy_device_credentials payload."""
    p = payload.copy()
    if "source" in p:
        p["source"] = _normalize_device_id(p["source"])
    if "destinations" in p:
        p["destinations"] = _normalize_device_ids(p["destinations"])
    # Ensure boolean credential flags are actual booleans
    for flag in ("snmpRead", "snmpWrite", "cli"):
        if flag in p:
            p[flag] = bool(p[flag])
        else:
            p.setdefault(flag, False)
    # userName trimmed
    if "userName" in p and isinstance(p["userName"], str):
        p["userName"] = p["userName"].strip()
    return p


def _normalize_get_credentials(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise get_device_detail_credentials payload."""
    p = payload.copy()
    if "deviceId" in p:
        p["deviceId"] = _normalize_device_id(p["deviceId"])
    return p


def _normalize_set_device_credentials(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise set_device_credentials payload (single device)."""
    p = payload.copy()
    if "deviceId" in p:
        p["deviceId"] = _normalize_device_id(p["deviceId"])
    for cred_key, is_write in (("snmpRead", False), ("snmpWrite", True)):
        if cred_key in p and isinstance(p[cred_key], dict):
            block = p[cred_key]
            # Normalise version
            if "version" in block:
                block["version"] = _normalize_snmp_version(block["version"])
            p[cred_key] = _apply_snmp_defaults(block, is_write=is_write)
    if "cli" in p and isinstance(p["cli"], dict):
        p["cli"] = _apply_cli_defaults(p["cli"])
    return p


def _normalize_set_bulk_credentials(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise set_bulk_device_credentials payload."""
    p = payload.copy()
    if "deviceId" in p:
        p["deviceId"] = _normalize_device_ids(p["deviceId"])
    return _normalize_set_device_credentials(p)


def _normalize_delete_credentials(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise delete_device_credentials payload."""
    p = payload.copy()
    if "deviceIds" in p:
        p["deviceIds"] = _normalize_device_ids(p["deviceIds"])
    return p


def _normalize_trust_untrust(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise trust/untrust device payload."""
    p = payload.copy()
    if "deviceIds" in p:
        p["deviceIds"] = _normalize_device_ids(p["deviceIds"])
    return p


def _normalize_get_certificate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise get_https_certificate payload – lowercase cert type."""
    p = payload.copy()
    if "deviceId" in p:
        p["deviceId"] = _normalize_device_id(p["deviceId"])
    if "type" in p and isinstance(p["type"], str):
        p["type"] = p["type"].lower().strip()
    return p


# ── Dispatch table ──────────────────────────────────────────────────────────────
_TOOL_NORMALIZERS = {
    "copy_device_credentials":      _normalize_copy_credentials,
    "get_device_detail_credentials": _normalize_get_credentials,
    "get_all_device_credentials":    lambda p: p,
    "set_device_credentials":        _normalize_set_device_credentials,
    "set_bulk_device_credentials":   _normalize_set_bulk_credentials,
    "delete_device_credentials":     _normalize_delete_credentials,
    "trust_device_credentials":      _normalize_trust_untrust,
    "untrust_device_credentials":    _normalize_trust_untrust,
    "get_https_certificate":         _normalize_get_certificate,
    "get_https_port":                _normalize_get_credentials,
    "get_default_device_credentials": lambda p: p,
    "view_decrypted_password":       lambda p: p,
    "check_role_rights_credentials": lambda p: p,
}


def normalize_payload(payload: Dict[str, Any], capability: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a payload for a given capability.

    Steps:
    1. Apply tool-specific field normalizations (device IDs, SNMP version,
       credential type flags, port defaults).
    2. Trim all top-level string fields.
    3. Remove None values for optional fields (keep required ones).

    Args:
        payload:    Raw payload extracted by LLM
        capability: Full capability card (from credential_api_schema_rag.json)

    Returns:
        Cleaned, normalized payload ready for validation and execution.
    """
    tool_name = capability.get("name", "")
    normalizer = _TOOL_NORMALIZERS.get(tool_name)

    if normalizer:
        try:
            payload = normalizer(payload)
            logger.debug(f"Applied tool-specific normalizer for {tool_name}")
        except Exception as e:
            logger.warning(f"Tool normalizer for {tool_name} failed: {e}")

    # Generic: trim all top-level string values
    for key, val in list(payload.items()):
        if isinstance(val, str):
            payload[key] = val.strip()

    # Remove None values, but keep required fields
    required = capability.get("input_schema", {}).get("required", [])
    payload = {k: v for k, v in payload.items() if v is not None or k in required}

    logger.info(f"Normalized payload for {tool_name}: {payload}")
    return payload
