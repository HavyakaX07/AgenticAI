# Test script for NL → API Orchestrator (PowerShell)

$BaseUrl = "http://localhost:8080"

Write-Host "🧪 Testing NL → API Orchestrator" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health check
Write-Host "Test 1: Health Check" -ForegroundColor Yellow
Write-Host "--------------------"
Invoke-RestMethod -Uri "$BaseUrl/health" | ConvertTo-Json -Depth 10
Write-Host ""
Write-Host ""

# Test 2: Successful orchestration
Write-Host "Test 2: Successful Orchestration (Complete Query)" -ForegroundColor Yellow
Write-Host "--------------------------------------------------"
Write-Host "Query: 'Open urgent ticket for payment failure'"
$body = @{query="Open urgent ticket for payment failure"} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl/orchestrate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10
Write-Host ""
Write-Host ""

# Test 3: Missing information
Write-Host "Test 3: Missing Information (ASK_USER)" -ForegroundColor Yellow
Write-Host "---------------------------------------"
Write-Host "Query: 'Create a ticket'"
$body = @{query="Create a ticket"} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl/orchestrate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10
Write-Host ""
Write-Host ""

# Test 4: List tickets
Write-Host "Test 4: List Tickets" -ForegroundColor Yellow
Write-Host "--------------------"
Write-Host "Query: 'Show me all open tickets'"
$body = @{query="Show me all open tickets"} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl/orchestrate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10
Write-Host ""
Write-Host ""

# Test 5: No matching tool
Write-Host "Test 5: No Matching Tool (NONE)" -ForegroundColor Yellow
Write-Host "--------------------------------"
Write-Host "Query: 'What is the weather today?'"
$body = @{query="What is the weather today?"} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl/orchestrate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10
Write-Host ""
Write-Host ""

# Test 6: Priority normalization
Write-Host "Test 6: Priority Normalization" -ForegroundColor Yellow
Write-Host "-------------------------------"
Write-Host "Query: 'Create asap ticket for server crash'"
$body = @{query="Create asap ticket for server crash with critical database errors"} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl/orchestrate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10
Write-Host ""
Write-Host ""

# Test 7: Filter tickets by priority
Write-Host "Test 7: Filter Tickets" -ForegroundColor Yellow
Write-Host "----------------------"
Write-Host "Query: 'List all urgent tickets'"
$body = @{query="List all urgent tickets"} | ConvertTo-Json
Invoke-RestMethod -Uri "$BaseUrl/orchestrate" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10
Write-Host ""
Write-Host ""

Write-Host "✅ All tests completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Check metrics at: http://localhost:8080/metrics"
Write-Host "📈 View dashboard at: http://localhost:3000"
Write-Host "🔍 View traces at: http://localhost:16686"

