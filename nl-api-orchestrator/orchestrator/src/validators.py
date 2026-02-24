"""
JSON Schema validation for payloads.
"""
import logging
from typing import Dict, Any, Tuple
from jsonschema import validate, ValidationError, Draft7Validator

logger = logging.getLogger(__name__)


def validate_payload(payload: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a payload against a JSON schema.

    Args:
        payload: The payload to validate
        schema: JSON Schema to validate against

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    try:
        # Use Draft7Validator for better error messages
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(payload))

        if not errors:
            logger.debug("Payload validation passed")
            return True, ""

        # Collect all validation errors
        error_messages = []
        for error in errors:
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            error_messages.append(f"{path}: {error.message}")

        error_str = "; ".join(error_messages)
        logger.warning(f"Payload validation failed: {error_str}")
        return False, error_str

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return False, f"Validation exception: {str(e)}"


def get_required_fields(schema: Dict[str, Any]) -> list:
    """
    Extract required field names from a JSON schema.

    Args:
        schema: JSON Schema

    Returns:
        List of required field names
    """
    return schema.get("required", [])


def get_missing_fields(payload: Dict[str, Any], schema: Dict[str, Any]) -> list:
    """
    Get list of missing required fields.

    Args:
        payload: The payload to check
        schema: JSON Schema with required fields

    Returns:
        List of missing required field names
    """
    required = get_required_fields(schema)
    missing = [field for field in required if field not in payload or payload[field] is None]
    return missing

