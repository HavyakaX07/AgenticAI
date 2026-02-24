#!/bin/bash
# Test script for NL → API Orchestrator

set -e

BASE_URL="http://localhost:8080"

echo "🧪 Testing NL → API Orchestrator"
echo "================================="
echo ""

# Test 1: Health check
echo "Test 1: Health Check"
echo "--------------------"
curl -s "$BASE_URL/health" | jq
echo ""
echo ""

# Test 2: Successful orchestration
echo "Test 2: Successful Orchestration (Complete Query)"
echo "--------------------------------------------------"
echo "Query: 'Open urgent ticket for payment failure'"
curl -s -X POST "$BASE_URL/orchestrate" \
  -H "Content-Type: application/json" \
  -d '{"query":"Open urgent ticket for payment failure"}' | jq
echo ""
echo ""

# Test 3: Missing information
echo "Test 3: Missing Information (ASK_USER)"
echo "---------------------------------------"
echo "Query: 'Create a ticket'"
curl -s -X POST "$BASE_URL/orchestrate" \
  -H "Content-Type: application/json" \
  -d '{"query":"Create a ticket"}' | jq
echo ""
echo ""

# Test 4: List tickets
echo "Test 4: List Tickets"
echo "--------------------"
echo "Query: 'Show me all open tickets'"
curl -s -X POST "$BASE_URL/orchestrate" \
  -H "Content-Type: application/json" \
  -d '{"query":"Show me all open tickets"}' | jq
echo ""
echo ""

# Test 5: No matching tool
echo "Test 5: No Matching Tool (NONE)"
echo "--------------------------------"
echo "Query: 'What is the weather today?'"
curl -s -X POST "$BASE_URL/orchestrate" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the weather today?"}' | jq
echo ""
echo ""

# Test 6: Priority normalization
echo "Test 6: Priority Normalization"
echo "-------------------------------"
echo "Query: 'Create asap ticket for server crash'"
curl -s -X POST "$BASE_URL/orchestrate" \
  -H "Content-Type: application/json" \
  -d '{"query":"Create asap ticket for server crash with critical database errors"}' | jq
echo ""
echo ""

# Test 7: Filter tickets by priority
echo "Test 7: Filter Tickets"
echo "----------------------"
echo "Query: 'List all urgent tickets'"
curl -s -X POST "$BASE_URL/orchestrate" \
  -H "Content-Type: application/json" \
  -d '{"query":"List all urgent tickets"}' | jq
echo ""
echo ""

echo "✅ All tests completed!"
echo ""
echo "📊 Check metrics at: http://localhost:8080/metrics"
echo "📈 View dashboard at: http://localhost:3000"
echo "🔍 View traces at: http://localhost:16686"

