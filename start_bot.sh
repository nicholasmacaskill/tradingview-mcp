#!/bin/bash

# Ensure we are in the project directory
cd "$(dirname "$0")"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found. Please run installation first."
    exit 1
fi

echo "🚀 Starting ICT Market Analyst Bot..."
echo "Logs will be saved to market_analyst.log"
echo "Briefs will be saved to briefs/"

# Run the analyst script
python3 market_analyst.py
