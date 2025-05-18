#!/usr/bin/env bash

set -e

# 1. Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it from https://github.com/astral-sh/uv"
    exit 1
fi

# 2. Sync the project with uv
uv sync

# 3. Activate venv
source .venv/bin/activate

# 4. Run the server
uvicorn app.main:app --port 8001
