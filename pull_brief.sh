#!/bin/bash

# Configuration
PROJECT_DIR="/Users/nicholasmacaskill/tradingview-mcp"
VENV_DIR="$PROJECT_DIR/.venv"

# Navigate to project directory
cd "$PROJECT_DIR"

# Check if ticker is provided as argument
TICKER_ARG=""
if [ ! -z "$1" ]; then
    TICKER_ARG="--ticker $1"
fi

# Run the analyst script once
echo "🚀 Requesting an on-demand ICT Investment Brief..."
"$VENV_DIR/bin/python3" "market_analyst.py" --once $TICKER_ARG
