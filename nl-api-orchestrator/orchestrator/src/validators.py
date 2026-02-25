"""
JSON Schema validation for NMS credential management payloads.
Adds SNMP conditional validation from nlp_metadata validation_rules.
"""
import logging
from typing import Dict, Any, Tuple, List
from jsonschema import validate, ValidationError, Draft7Validator

logger = logging.getLogger(__name__)

# ── SNMP conditional validation rules (from nlp_metadata.validation_rules) ─────
# version 1/2: need readCommunity (snmpRead) or writeCommunity (snmpWrite)
# version 3:   need userName + securityLevel
_SNMP_V1V2_READ_REQUIRED  = ["readCommunity"]
_SNMP_V1V2_WRITE_REQUIRED = ["writeCommunity"]
_SNMP_V3_REQUIRED         = ["userName", "securityLevel"]


def _validate_snmp_block(block: Dict[str, Any], block_name: str, is_write: bool = False) -> List[str]:
    """
    Validate an SNMP credential block for version-conditional required fields
    as specified in nlp_metadata.validation_rules.

    Returns a list of error strings (empty = valid).
    """
    errors = []
    version = block.get("version")
    if version is None:
        errors.append(f"{block_name}.version is required")
        return errors

    try:
        version = int(version)
    except (ValueError, TypeError):
        errors.append(f"{block_name}.version must be 1, 2, or 3 (got {version!r})")
        return errors

    if version in (1, 2):
        required = _SNMP_V1V2_WRITE_REQUIRED if is_write else _SNMP_V1V2_READ_REQUIRED
        for field in required:
            if not block.get(field):
                errors.append(f"{block_name}.{field} is required for SNMP v{version}")
    elif version == 3:
        for field in _SNMP_V3_REQUIRED:
            if not block.get(field):
                errors.append(f"{block_name}.{field} is required for SNMP v3")
    else:
        errors.append(f"{block_name}.version must be 1, 2, or 3 (got {version})")

    return errors


def validate_payload(payload: Dict[str, Any], schema: Dict[str, Any],
                     tool_name: str = "") -> Tuple[bool, str]:
    """
    Validate a payload against its JSON schema, then apply NMS-specific
    conditional validation rules for SNMP credential blocks.

    Args:
        payload:   The payload dict to validate
        schema:    JSON Schema from credential_api_schema_rag.json
        tool_name: Optional tool name for targeted conditional checks

    Returns:
        (is_valid, error_message)  –  error_message is "" on success.
    """
    # ── 1. JSON-Schema structural validation ──────────────────────────────────
    try:
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(payload))

        if errors:
            messages = []
            for err in errors:
                path = ".".join(str(p) for p in err.path) if err.path else "root"
                messages.append(f"{path}: {err.message}")
            error_str = "; ".join(messages)
            logger.warning(f"Schema validation failed for {tool_name}: {error_str}")
            return False, error_str

    except Exception as e:
        logger.error(f"Validation exception for {tool_name}: {e}", exc_info=True)
        return False, f"Validation exception: {str(e)}"

    # ── 2. NMS conditional SNMP validation ────────────────────────────────────
    snmp_errors: List[str] = []

    # set_device_credentials and set_bulk_device_credentials carry SNMP blocks
    if tool_name in ("set_device_credentials", "set_bulk_device_credentials"):
        if "snmpRead" in payload and isinstance(payload["snmpRead"], dict):
            snmp_errors.extend(
                _validate_snmp_block(payload["snmpRead"], "snmpRead", is_write=False)
            )
        if "snmpWrite" in payload and isinstance(payload["snmpWrite"], dict):
            snmp_errors.extend(
                _validate_snmp_block(payload["snmpWrite"], "snmpWrite", is_write=True)
            )

    if snmp_errors:
        error_str = "; ".join(snmp_errors)
        logger.warning(f"SNMP conditional validation failed for {tool_name}: {error_str}")
        return False, error_str

    logger.debug(f"Payload validation passed for {tool_name}")
    return True, ""


def get_required_fields(schema: Dict[str, Any]) -> List[str]:
    """Return the list of required field names from a JSON schema."""
    return schema.get("required", [])


def get_missing_fields(payload: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Return required fields that are absent or None in the payload."""
    required = get_required_fields(schema)
    return [f for f in required if not payload.get(f)]
