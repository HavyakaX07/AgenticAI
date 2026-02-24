# Complete OPA Fix Verification Test
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OPA Policy Fix Verification" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test 1: Query entire policy package (new approach)
Write-Host "Test 1: Query /v1/data/policy (returns allow + reason)" -ForegroundColor Yellow
Write-Host "--------------------------------------------------------" -ForegroundColor Yellow
$body1 = @{
    input = @{
        risk = "low"
        payload = @{
            description = "test operation"
        }
    }
} | ConvertTo-Json -Depth 5

try {
    $response1 = Invoke-RestMethod -Uri "http://localhost:8181/v1/data/policy" -Method Post -Body $body1 -ContentType "application/json"
    Write-Host "✓ Success!" -ForegroundColor Green
    Write-Host "Response structure:" -ForegroundColor Cyan
    Write-Host ($response1 | ConvertTo-Json -Depth 5) -ForegroundColor White
    Write-Host "`nResult type: $($response1.result.GetType().Name)" -ForegroundColor Cyan
    if ($response1.result.allow) {
        Write-Host "✓ allow = $($response1.result.allow)" -ForegroundColor Green
    } else {
        Write-Host "✗ allow = $($response1.result.allow)" -ForegroundColor Red
        Write-Host "  reason = $($response1.result.reason)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host "`n========================================`n" -ForegroundColor Cyan

# Test 2: Query specific rule /allow (old approach - returns boolean)
Write-Host "Test 2: Query /v1/data/policy/allow (returns boolean only)" -ForegroundColor Yellow
Write-Host "--------------------------------------------------------" -ForegroundColor Yellow
try {
    $response2 = Invoke-RestMethod -Uri "http://localhost:8181/v1/data/policy/allow" -Method Post -Body $body1 -ContentType "application/json"
    Write-Host "✓ Success!" -ForegroundColor Green
    Write-Host "Response structure:" -ForegroundColor Cyan
    Write-Host ($response2 | ConvertTo-Json -Depth 5) -ForegroundColor White
    Write-Host "`nResult type: $($response2.result.GetType().Name)" -ForegroundColor Cyan
    Write-Host "Result value: $($response2.result)" -ForegroundColor White
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host "`n========================================`n" -ForegroundColor Cyan

# Test 3: Denial case with reason
Write-Host "Test 3: High-risk without confirmation (should deny with reason)" -ForegroundColor Yellow
Write-Host "--------------------------------------------------------" -ForegroundColor Yellow
$body3 = @{
    input = @{
        risk = "high"
        confirmed = $false
        payload = @{
            description = "dangerous operation"
        }
    }
} | ConvertTo-Json -Depth 5

try {
    $response3 = Invoke-RestMethod -Uri "http://localhost:8181/v1/data/policy" -Method Post -Body $body3 -ContentType "application/json"
    Write-Host "✓ Success!" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Cyan
    Write-Host ($response3 | ConvertTo-Json -Depth 5) -ForegroundColor White
    if (-not $response3.result.allow) {
        Write-Host "`n✓ Correctly denied" -ForegroundColor Green
        Write-Host "  Reason: $($response3.result.reason)" -ForegroundColor Yellow
    } else {
        Write-Host "`n✗ Should have been denied!" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host "`n========================================`n" -ForegroundColor Cyan

# Check container status
Write-Host "Container Status:" -ForegroundColor Yellow
Write-Host "--------------------------------------------------------" -ForegroundColor Yellow
docker-compose -f docker-compose.poc.yml ps orchestrator
docker-compose -f docker-compose.poc.yml ps mcp-policy

Write-Host "`n========================================`n" -ForegroundColor Cyan
Write-Host "Verification Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

