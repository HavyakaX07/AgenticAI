"""
NMS Credential Management – Tool Registry.
All 13 tools from credential_api_schema_rag.json are registered here,
plus the device lookup tool used for resolving device references → device_ids.
"""
from .nms_credentials import (
    copy_device_credentials,
    get_device_detail_credentials,
    get_all_device_credentials,
    set_device_credentials,
    set_bulk_device_credentials,
    delete_device_credentials,
    trust_device_credentials,
    untrust_device_credentials,
    get_https_certificate,
    get_https_port,
    get_default_device_credentials,
    view_decrypted_password,
    check_role_rights_credentials,
)
from .nms_device_lookup import resolve_device_ids

# Registry: tool_name → async handler function
TOOLS = {
    # ── Device resolution (always called first when device refs are ambiguous) ──
    "resolve_device_ids":             resolve_device_ids,

    # ── NMS Credential Management ───────────────────────────────────────────────
    "copy_device_credentials":        copy_device_credentials,
    "get_device_detail_credentials":  get_device_detail_credentials,
    "get_all_device_credentials":     get_all_device_credentials,
    "set_device_credentials":         set_device_credentials,
    "set_bulk_device_credentials":    set_bulk_device_credentials,
    "delete_device_credentials":      delete_device_credentials,
    "trust_device_credentials":       trust_device_credentials,
    "untrust_device_credentials":     untrust_device_credentials,
    "get_https_certificate":          get_https_certificate,
    "get_https_port":                 get_https_port,
    "get_default_device_credentials": get_default_device_credentials,
    "view_decrypted_password":        view_decrypted_password,
    "check_role_rights_credentials":  check_role_rights_credentials,
}

__all__ = ["TOOLS"]
