# Test OPA Policy Endpoint
Write-Host "Testing OPA Policy Endpoint..." -ForegroundColor Cyan

# Test 1: Low risk - should allow
Write-Host "`n=== Test 1: Low Risk Operation ===" -ForegroundColor Yellow
$body1 = @{
    input = @{
        risk = "low"
        payload = @{
            description = "test operation"
        }
    }
} | ConvertTo-Json -Depth 5

try {
    $response1 = Invoke-RestMethod -Uri "http://localhost:8181/v1/data/policy/allow" -Method Post -Body $body1 -ContentType "application/json"
    Write-Host "Response: $($response1 | ConvertTo-Json -Depth 5)" -ForegroundColor Green
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
}

# Test 2: High risk without confirmation - should deny
Write-Host "`n=== Test 2: High Risk Without Confirmation ===" -ForegroundColor Yellow
$body2 = @{
    input = @{
        risk = "high"
        confirmed = $false
        payload = @{
            description = "dangerous operation that needs confirmation"
        }
    }
} | ConvertTo-Json -Depth 5

try {
    $response2 = Invoke-RestMethod -Uri "http://localhost:8181/v1/data/policy/allow" -Method Post -Body $body2 -ContentType "application/json"
    Write-Host "Response: $($response2 | ConvertTo-Json -Depth 5)" -ForegroundColor Green
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

# Check container status
Write-Host "`n=== Container Status ===" -ForegroundColor Yellow
docker-compose -f docker-compose.poc.yml ps

