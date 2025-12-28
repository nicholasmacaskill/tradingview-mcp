# Walkthrough: ICT Market Analyst Bot

## Overview
You now have a fully automated "Market Analyst" that:
1.  **Wakes up** every hour.
2.  **Fetches** TradingView charts for your defined tickers and timeframes.
3.  **Analyzes** them using an AI Vision model (ICT Style).
4.  **Logs** the detailed reports.

## Setup

### 1. API Key (Required for Analysis)
To enable the "Brain", you must add an API key to your `.env` file.
The script supports `openai` (default) or `google-generativeai`.

**Edit `.env`:**
```bash
# Add your key
LLM_API_KEY=your_key_here
# Optional: Set provider (openai or gemini)
LLM_PROVIDER=openai 
```

### 2. Python Requirements
The analyst script handles its own dependencies and **works on your current Python 3.9**.
*(Note: The full MCP server still needs Python 3.10+, but this bot is standalone).*

## Usage

### Running the Bot
To start the automation, run:

```bash
cd /Users/nicholasmacaskill/tradingview-mcp
.venv/bin/python3 market_analyst.py
```

The bot will print logs to the console and run indefinitely.

### Viewing Results
*   **Console**: Real-time updates and analysis summaries.
*   **Log File**: Detailed logs are saved to `market_analyst.log`.
*   **Report File**: `analysis_log.md` (created once analysis runs successfully).

## Configuration
You can customize tickers and timeframes by editing `market_analyst.py`:

```python
# market_analyst.py
TICKERS = ["BYBIT:BTCUSDT.P", "BYBIT:ETHUSDT.P"] 
TIMEFRAMES = ["5", "15", "60", "240", "D"]
```
