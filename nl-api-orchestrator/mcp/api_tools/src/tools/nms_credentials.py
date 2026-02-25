"""
NMS Credential Management – MCP Tool Implementations.

All 13 tools defined in credential_api_schema_rag.json are implemented here.
POC mode: returns realistic mock responses.
Production: swap the mock blocks for real httpx calls to https://api.sinecnms.com
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _ok(**kwargs) -> Dict[str, Any]:
    return {"status": True, "errorCode": "SUCCESS", **kwargs}

def _err(code: str, msg: str) -> Dict[str, Any]:
    return {"status": False, "errorCode": code, "message": msg}


# ── 1. copy_device_credentials ─────────────────────────────────────────────────

async def copy_device_credentials(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Copy credentials from one source device to multiple destination devices.
    Supports selective copying of SNMP read, SNMP write, and CLI credentials.

    Required: source (str), destinations (list[str]), userName (str)
    Optional: snmpRead (bool), snmpWrite (bool), cli (bool)
    """
    source       = args.get("source", "")
    destinations = args.get("destinations", [])
    snmp_read    = args.get("snmpRead",  False)
    snmp_write   = args.get("snmpWrite", False)
    cli          = args.get("cli",       False)
    user_name    = args.get("userName",  "system")

    if not source:
        return _err("INVALID_COPY_CREDENTIAL_FORMAT_DATA", "source device is required")
    if not destinations:
        return _err("INVALID_COPY_CREDENTIAL_FORMAT_DATA", "destinations list is required")

    copied_types = [t for t, flag in [("SNMP Read", snmp_read), ("SNMP Write", snmp_write), ("CLI", cli)] if flag]
    logger.info(f"[mock] copy_device_credentials: {source} → {destinations} types={copied_types} by={user_name}")

    return _ok(
        message="Credential Copy action success",
        source=source,
        destinations=destinations,
        credentials_copied=len(destinations),
        copied_types=copied_types,
    )


# ── 2. get_device_detail_credentials ──────────────────────────────────────────

async def get_device_detail_credentials(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Retrieve detailed credentials for a specific device including SNMP read,
    SNMP write, and CLI settings.

    Required: deviceId (str)
    """
    device_id = args.get("deviceId", "")
    if not device_id:
        return _err("INVALID_FORMAT_DATA", "deviceId is required")

    logger.info(f"[mock] get_device_detail_credentials: deviceId={device_id}")

    return _ok(
        deviceId=device_id,
        snmpRead={
            "version": 3,
            "port": 161,
            "retries": 3,
            "timeout": 5,
            "securityLevel": 3,
            "userName": "snmpv3user",
            "authAlgo": 1,
            "encryptAlgo": 1,
        },
        snmpWrite={
            "version": 2,
            "port": 161,
            "writeCommunity": "**encrypted**",
        },
        cli={
            "userId": "admin",
            "password": "**encrypted**",
            "sshPort": 22,
            "retryCount": 3,
            "retryTimeout": 30,
            "netconfPort": 830,
            "httpsPort": 443,
        },
    )


# ── 3. get_all_device_credentials ─────────────────────────────────────────────

async def get_all_device_credentials(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Retrieve a list of all devices in the credential repository.
    """
    logger.info("[mock] get_all_device_credentials")
    return _ok(
        total=3,
        devices=[
            {"deviceId": "device-001", "snmpConfigured": True,  "cliConfigured": True},
            {"deviceId": "device-002", "snmpConfigured": True,  "cliConfigured": False},
            {"deviceId": "device-003", "snmpConfigured": False, "cliConfigured": True},
        ],
    )


# ── 4. set_device_credentials ─────────────────────────────────────────────────

async def set_device_credentials(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Set or update credentials for a single device.
    Supports SNMP read, SNMP write, and CLI credential blocks.

    Required: deviceId (str)
    Optional: snmpRead (obj), snmpWrite (obj), cli (obj),
              snmpReadCredChange (bool), snmpWriteCredChange (bool), cliCredChange (bool)
    """
    device_id = args.get("deviceId", "")
    if not device_id:
        return _err("INVALID_FORMAT_DATA", "deviceId is required")

    changed = [k for k in ("snmpReadCredChange", "snmpWriteCredChange", "cliCredChange") if args.get(k)]
    logger.info(f"[mock] set_device_credentials: deviceId={device_id} changed={changed}")

    return _ok(
        message="Credentials updated successfully",
        deviceId=device_id,
        updated=changed,
    )


# ── 5. set_bulk_device_credentials ────────────────────────────────────────────

async def set_bulk_device_credentials(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Set or update credentials for multiple devices in bulk.

    Required: deviceId (list[str])
    Optional: same credential blocks as set_device_credentials
    """
    device_ids = args.get("deviceId", [])
    if not device_ids:
        return _err("INVALID_FORMAT_DATA", "deviceId list is required")

    count = len(device_ids) if isinstance(device_ids, list) else 1
    logger.info(f"[mock] set_bulk_device_credentials: count={count}")

    return _ok(
        message=f"Bulk credential update success for {count} device(s)",
        updated_count=count,
        device_ids=device_ids,
    )


# ── 6. delete_device_credentials ──────────────────────────────────────────────

async def delete_device_credentials(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Delete credentials for one or more devices.

    Required: deviceIds (list[str])
    """
    device_ids = args.get("deviceIds", [])
    if not device_ids:
        return _err("INVALID_FORMAT_DATA", "deviceIds list is required")

    count = len(device_ids) if isinstance(device_ids, list) else 1
    logger.info(f"[mock] delete_device_credentials: count={count} ids={device_ids}")

    return _ok(
        message=f"Successfully deleted credentials for {count} device(s)",
        deleted_count=count,
        device_ids=device_ids,
    )


# ── 7. trust_device_credentials ───────────────────────────────────────────────

async def trust_device_credentials(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Trust the SSH fingerprint or certificate for one or more devices.

    Required: deviceIds (list[str])
    """
    device_ids = args.get("deviceIds", [])
    if not device_ids:
        return _err("INVALID_FORMAT_DATA", "deviceIds list is required")

    logger.info(f"[mock] trust_device_credentials: ids={device_ids}")
    return _ok(
        message=f"Trust accepted for {len(device_ids)} device(s)",
        trusted=device_ids,
    )


# ── 8. untrust_device_credentials ─────────────────────────────────────────────

async def untrust_device_credentials(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Revoke trust (SSH fingerprint / certificate) for one or more devices.

    Required: deviceIds (list[str])
    """
    device_ids = args.get("deviceIds", [])
    if not device_ids:
        return _err("INVALID_FORMAT_DATA", "deviceIds list is required")

    logger.info(f"[mock] untrust_device_credentials: ids={device_ids}")
    return _ok(
        message=f"Trust revoked for {len(device_ids)} device(s)",
        untrusted=device_ids,
    )


# ── 9. get_https_certificate ──────────────────────────────────────────────────

async def get_https_certificate(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Retrieve the HTTPS/SSL certificate for a device.

    Required: deviceId (str), type (str)
    """
    device_id = args.get("deviceId", "")
    cert_type = args.get("type", "https")

    if not device_id:
        return _err("INVALID_FORMAT_DATA", "deviceId is required")

    logger.info(f"[mock] get_https_certificate: deviceId={device_id} type={cert_type}")
    return _ok(
        deviceId=device_id,
        type=cert_type,
        certificate={
            "subject": f"CN={device_id}",
            "issuer": "Mock CA",
            "valid_from": "2025-01-01",
            "valid_until": "2026-12-31",
            "fingerprint": "AA:BB:CC:DD:EE:FF",
        },
    )


# ── 10. get_https_port ────────────────────────────────────────────────────────

async def get_https_port(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Retrieve the HTTPS port configured for a device.

    Required: deviceId (str)
    """
    device_id = args.get("deviceId", "")
    if not device_id:
        return _err("INVALID_FORMAT_DATA", "deviceId is required")

    logger.info(f"[mock] get_https_port: deviceId={device_id}")
    return _ok(deviceId=device_id, httpsPort=443)


# ── 11. get_default_device_credentials ────────────────────────────────────────

async def get_default_device_credentials(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Retrieve the system default credential template used for new devices.
    """
    logger.info("[mock] get_default_device_credentials")
    return _ok(
        snmpRead={
            "version": 2,
            "port": 161,
            "retries": 3,
            "timeout": 5,
            "readCommunity": "**default_encrypted**",
        },
        cli={
            "sshPort": 22,
            "netconfPort": 830,
            "httpsPort": 443,
            "retryTimeout": 30,
        },
    )


# ── 12. view_decrypted_password ───────────────────────────────────────────────

async def view_decrypted_password(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Decrypt and return a stored encrypted password in plaintext.
    CRITICAL risk – requires confirmation.

    Required: encryptedPassword (str)
    """
    encrypted = args.get("encryptedPassword", "")
    if not encrypted:
        return _err("INVALID_FORMAT_DATA", "encryptedPassword is required")

    logger.info("[mock] view_decrypted_password: returning mock plaintext")
    # POC: never return a real password – just echo a masked mock value
    return _ok(decryptedPassword="mock-plain-text-p@ssword")


# ── 13. check_role_rights_credentials ─────────────────────────────────────────

async def check_role_rights_credentials(
    args: Dict[str, Any],
    allowlist: List[str],
    token: str,
) -> Dict[str, Any]:
    """
    Check the current user's role and permissions for credential management.
    """
    logger.info("[mock] check_role_rights_credentials")
    return _ok(
        role="NETWORK_OPERATOR",
        rights={
            "CREDENTIAL_REPOSITORY": ["VIEW", "EDIT"],
        },
        canCopy=True,
        canDelete=False,
        canBulkUpdate=False,
        canViewDecrypted=False,
    )

