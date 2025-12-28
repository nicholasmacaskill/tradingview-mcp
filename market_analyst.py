import os
import time
import logging
import asyncio
import base64
import re
import requests
import subprocess
from io import BytesIO
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from tview_scraper import TradingViewScraper, TradingViewScraperError
from ict_prompt import ICT_SYSTEM_PROMPT
from openai import OpenAI
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("market_analyst.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
TICKERS = ["BYBIT:BTCUSDT.P"]
TIMEFRAMES = ["5", "15", "60", "240", "D"]

# Multi-Provider Configuration
GEMINI_API_KEY = os.getenv("LLM_API_KEY_GEMINI") or os.getenv("LLM_API_KEY")
OPENAI_API_KEY = os.getenv("LLM_API_KEY_OPENAI")
PRIMARY_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

def analyze_image_with_llm(image_data_uri, ticker, interval):
    """
    Sends the image to an LLM for ICT analysis with Circuit Breaker / Fallback logic.
    Cycles through multiple FREE Gemini models to maximize daily quota.
    """
    if not GEMINI_API_KEY:
        logger.warning("⚠️ No LLM_API_KEY found. Skipping analysis step.")
        return "Analysis skipped (No API Key)"

    # List of free models to try in order (Matched to your specific account)
    model_names = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-pro-vision", "gemini-flash-latest"]
    
    for model_name in model_names:
        logger.info(f"🧠 Attempting analysis with {model_name.upper()}...")
        
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            # Use beta version for some newer models if needed
            model = genai.GenerativeModel(model_name)
            
            # Extract image for Gemini
            header, encoded = image_data_uri.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            image = Image.open(BytesIO(image_bytes))
            
            response = model.generate_content([ICT_SYSTEM_PROMPT, image])
            return response.text

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning(f"⚠️ {model_name.upper()} Quota Exceeded. Activating Circuit Breaker (15s wait)...")
                time.sleep(15)
                continue # Try next free model
            else:
                logger.error(f"❌ {model_name.upper()} failed: {e}")
                continue # Try next free model

    return "❌ Error: All free Gemini models failed or daily quota exceeded."

def trigger_notification(score, ticker):
    """Triggers a Mac terminal alert for high confidence setups."""
    msg = f"🚀 ANTIGRAVITY ALERT: {ticker} Confidence Score: {score}!"
    logger.info(f"🔔 {msg}")
    try:
        # Mac osascript for system notification
        cmd = f'display notification "{msg}" with title "Market Analyst Bot" sound name "Glass"'
        subprocess.run(["osascript", "-e", cmd])
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

def run_analysis_cycle():
    """Runs one full cycle of analysis with visual optimizations."""
    logger.info("🚀 Starting analysis cycle...")
    os.makedirs("briefs/images", exist_ok=True)
    
    headless = os.getenv("MCP_SCRAPER_HEADLESS", "True").lower() == "true"
    window_width = int(os.getenv("MCP_SCRAPER_WINDOW_WIDTH", "1400"))
    window_height = int(os.getenv("MCP_SCRAPER_WINDOW_HEIGHT", "1400"))
    chart_layout = os.getenv("TRADINGVIEW_CHART_LAYOUT", "6EmwLGbc")
    
    try:
        with TradingViewScraper(headless=headless, window_size=f"{window_width},{window_height}", chart_page_id=chart_layout, use_save_shortcut=True) as scraper:
            for ticker in TICKERS:
                timestamp = time.strftime("%Y%m%d_%H%M")
                ticker_clean = ticker.replace(":", "_")
                images_data = []
                
                # 1. Fetch charts
                for interval in TIMEFRAMES:
                    try:
                        logger.info(f"  📸 Fetching: {ticker} [{interval}]")
                        # Add stabilization sleep for indicators to render
                        time.sleep(5) 
                        image_url = scraper.get_chart_image_url(ticker, interval)
                        if image_url:
                            if image_url.startswith("data:image"):
                                header, encoded = image_url.split(",", 1)
                                image_bytes = base64.b64decode(encoded)
                            else:
                                image_bytes = requests.get(image_url).content
                            
                            img_filename = f"{ticker_clean}_{interval}_{timestamp}.png"
                            img_path = os.path.join("briefs/images", img_filename)
                            with open(img_path, "wb") as f:
                                f.write(image_bytes)
                                
                            img = Image.open(BytesIO(image_bytes))
                            images_data.append({"interval": interval, "img": img, "filename": img_filename})
                    except Exception as e:
                        logger.error(f"  ❌ Error fetching {interval}: {e}")

                if not images_data: continue

                # 2. Build Grid
                total_height = sum(d["img"].size[1] for d in images_data) + (len(images_data) * 40)
                max_width = max(d["img"].size[0] for d in images_data)
                grid_img = Image.new('RGB', (max_width, total_height), (255, 255, 255))
                y_offset = 0
                
                for d in images_data:
                    draw = ImageDraw.Draw(grid_img)
                    draw.text((10, y_offset + 5), f"Timeframe: {d['interval']}", fill=(0, 0, 0))
                    y_offset += 30
                    grid_img.paste(d["img"], (0, y_offset))
                    y_offset += d["img"].size[1] + 10

                # 3. Analyze
                buffered = BytesIO()
                grid_img.save(buffered, format="PNG")
                grid_data_uri = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
                
                analysis = analyze_image_with_llm(grid_data_uri, ticker, "Top-Down Grid")
                
                # 4. Check for HTF_LEVEL and Visual Optimization
                # Note: Precisely mapping price to pixels requires OCR or fixed scales.
                # Here we implement the parsing logic as a foundation.
                level_match = re.search(r"\[HTF_LEVEL:\s*([\d\.]+)\]", analysis)
                if level_match:
                    level_price = level_match.group(1)
                    logger.info(f"📍 HTF Level detected: {level_price}. (Visual line logic requires price/pixel mapping).")
                    # Placeholder: Drawing a reference line at the top to indicate awareness
                    draw = ImageDraw.Draw(grid_img)
                    draw.line([(0, 15), (max_width, 15)], fill=(255, 0, 0), width=3)
                    draw.text((max_width - 150, 5), f"LVL: {level_price}", fill=(255, 0, 0))

                # 5. Check Confidence for Alerts
                conf_match = re.search(r"Confidence:\s*(\d+)", analysis)
                if conf_match:
                    score = int(conf_match.group(1))
                    if score > 8:
                        trigger_notification(score, ticker)

                # 6. Save and Push
                grid_filename = f"{ticker_clean}_grid_{timestamp}.png"
                grid_path = os.path.join("briefs/images", grid_filename)
                grid_img.save(grid_path)
                
                brief_content = [
                    f"# Investment Brief: {ticker}",
                    f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "## Top-Down Antigravity Analysis",
                    analysis.replace(f"[HTF_LEVEL: {level_price}]" if level_match else "", ""), # Clean tag from brief
                    "\n---\n",
                    "## Detailed Timeframe Charts"
                ]
                for d in images_data:
                    brief_content.append(f"### {d['interval']}\n![Chart](images/{d['filename']})")

                filename = f"briefs/Brief_{ticker_clean}_{timestamp}.md"
                with open(filename, "w") as f:
                    f.write("\n".join(brief_content))
                
                logger.info(f"✅ Brief saved: {filename}")

    except Exception as e:
        logger.critical(f"🔥 Critical Failure: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--ticker", type=str)
    args = parser.parse_args()

    if args.ticker: TICKERS = [args.ticker]
    if args.once:
        run_analysis_cycle()
    else:
        while True:
            run_analysis_cycle()
            time.sleep(3600)
