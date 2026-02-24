# Test OPA Response Format
Write-Host "Testing OPA Response Format..." -ForegroundColor Cyan

$body = @{
    input = @{
        risk = "low"
        payload = @{
            description = "test operation"
        }
        tool = "list_tickets"
    }
} | ConvertTo-Json -Depth 5

Write-Host "Request Body:" -ForegroundColor Yellow
Write-Host $body

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8181/v1/data/policy/allow" -Method Post -Body $body -ContentType "application/json"
    Write-Host "`nResponse:" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 5)
    Write-Host "`nResult type:" -ForegroundColor Yellow
    Write-Host $response.result.GetType().Name
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

