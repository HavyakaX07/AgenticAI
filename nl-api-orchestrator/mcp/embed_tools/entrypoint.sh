#!/bin/sh
# =============================================================================
# entrypoint.sh - MCP Embed Tools startup script
#
# 1. Downloads BAAI/bge-small-en-v1.5 via fastembed on FIRST run.
#    The model is cached at FASTEMBED_CACHE_PATH (/app/model_cache).
#    This path is mounted as a Docker named volume (embed-cache) so the
#    ~120 MB ONNX file is NOT re-downloaded on container restarts.
#
# 2. Starts the FastAPI/uvicorn server on port 9001.
# =============================================================================

set -e

MODEL="${EMBED_MODEL:-BAAI/bge-small-en-v1.5}"
CACHE_DIR="${FASTEMBED_CACHE_PATH:-/app/model_cache}"

echo "============================================================"
echo " MCP Embed Tools - Startup"
echo " Model      : $MODEL"
echo " Cache path : $CACHE_DIR"
echo "============================================================"

# Check if model is already cached (fastembed saves a folder per model)
# Model folder name = replace '/' with '-'
MODEL_FOLDER=$(echo "$MODEL" | tr '/' '-' | tr '[:upper:]' '[:lower:]')

if [ -d "$CACHE_DIR/fast-bge-small-en-v1.5" ] || \
   find "$CACHE_DIR" -name "*.onnx" 2>/dev/null | grep -q .; then
    echo "✓ Model already cached at $CACHE_DIR — skipping download"
else
    echo "⬇ Downloading $MODEL (first-time only, ~120 MB) ..."
    python -c "
import os
os.environ['FASTEMBED_CACHE_PATH'] = '$CACHE_DIR'
from fastembed import TextEmbedding
print('Initialising fastembed model download ...')
model = TextEmbedding('$MODEL')
# Force actual download by generating one embedding
list(model.embed(['warmup']))
print('Model downloaded and cached successfully!')
"
    echo "✓ Download complete"
fi

echo "Starting uvicorn on 0.0.0.0:9001 ..."
exec uvicorn src.server:app --host 0.0.0.0 --port 9001

