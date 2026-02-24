#!/bin/bash
# Quick start script for NL → API Orchestrator

set -e

echo "🚀 Starting NL → API Orchestrator..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
fi

echo "🐳 Building and starting Docker services..."
docker compose up -d --build

echo ""
echo "⏳ Waiting for services to be ready..."
echo ""

# Wait for orchestrator
echo "Checking orchestrator..."
for i in {1..30}; do
    if curl -f http://localhost:8080/health &>/dev/null; then
        echo "✅ Orchestrator is ready"
        break
    fi
    echo -n "."
    sleep 2
done

# Wait for vLLM (this takes longer)
echo ""
echo "Checking vLLM (this may take 2-5 minutes)..."
for i in {1..150}; do
    if curl -f http://localhost:8000/health &>/dev/null; then
        echo "✅ vLLM is ready"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "✨ All services are ready!"
echo ""
echo "📊 Service URLs:"
echo "  - Orchestrator API: http://localhost:8080"
echo "  - Orchestrator Health: http://localhost:8080/health"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo "  - Jaeger: http://localhost:16686"
echo "  - Traefik Dashboard: http://localhost:8090"
echo ""
echo "🧪 Test the orchestrator:"
echo "  curl -X POST http://localhost:8080/orchestrate \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"query\":\"Open urgent ticket for payment failure\"}' | jq"
echo ""
echo "📋 View logs:"
echo "  docker compose logs -f orchestrator"
echo ""
echo "🛑 Stop services:"
echo "  docker compose down"
echo ""

