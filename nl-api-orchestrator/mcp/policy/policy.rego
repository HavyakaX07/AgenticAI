package policy

# =============================================================================
# NMS Credential Management – Authorization Policy
#
# Risk levels are sourced from credential_api_nlp_metadata.security_levels:
#
#   low      – read-only ops (get, list, check)   → always allow
#   medium   – trust/untrust, certificate reads   → allow with valid user
#   high     – copy, set, delete credentials      → require confirmation
#   critical – bulk set, view decrypted password  → require confirmation
#              (+ additional verification in future)
# =============================================================================

# Default deny – safe by default
default allow = false

# ── Low-risk: always allow (view, list, check operations) ─────────────────────
allow if {
    input.risk == "low"
}

# ── Medium-risk: allow if a user identity is present ──────────────────────────
allow if {
    input.risk == "medium"
    input.user != ""
    input.user != null
}

# ── High-risk: require explicit confirmation (copy, set, delete credentials) ──
allow if {
    input.risk == "high"
    input.confirmed == true
}

# ── Critical-risk: require explicit confirmation (bulk set, decrypt password) ──
allow if {
    input.risk == "critical"
    input.confirmed == true
}

# =============================================================================
# Human-readable deny reasons
# =============================================================================

deny_reason := msg if {
    not allow
    input.risk == "high"
    not input.confirmed
    msg := "High-risk operation requires explicit confirmation (send confirmed=true)"
}

deny_reason := msg if {
    not allow
    input.risk == "critical"
    not input.confirmed
    msg := "Critical-risk operation requires explicit confirmation (send confirmed=true)"
}

deny_reason := msg if {
    not allow
    input.risk == "medium"
    not input.user
    msg := "Medium-risk operation requires an authenticated user"
}

deny_reason := "Policy check failed: unknown risk level or missing input" if {
    not allow
    not input.risk
}
