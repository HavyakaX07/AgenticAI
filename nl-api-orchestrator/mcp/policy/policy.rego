package policy

# Default deny
default allow = false

# Allow low-risk operations with valid payload
allow if {
    input.risk == "low"
    input.payload
}

# Allow medium-risk operations with sufficient description
allow if {
    input.risk == "medium"
    input.payload.description
    count(input.payload.description) >= 10
}

# High-risk operations require explicit confirmation
allow if {
    input.risk == "high"
    input.confirmed == true
    input.payload.description
    count(input.payload.description) >= 20
}

# Deny with reason
reason = msg if {
    not allow
    input.risk == "high"
    not input.confirmed
    msg := "High-risk operation requires explicit confirmation"
}

reason = msg if {
    not allow
    input.risk == "medium"
    not input.payload.description
    msg := "Medium-risk operations require a description"
}

reason = msg if {
    not allow
    input.risk == "medium"
    count(input.payload.description) < 10
    msg := "Description must be at least 10 characters for medium-risk operations"
}

reason = msg if {
    not allow
    input.risk == "high"
    input.confirmed == true
    count(input.payload.description) < 20
    msg := "Description must be at least 20 characters for high-risk operations"
}

reason = "Policy check failed" if {
    not allow
    not input.risk
}

