import os
import time
import logging
import asyncio
import base64
from dotenv import load_dotenv
from tview_scraper import TradingViewScraper, TradingViewScraperError
from ict_prompt import ICT_SYSTEM_PROMPT

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
TICKERS = ["BYBIT:BTCUSDT.P"] # Only BTC per user request
TIMEFRAMES = ["5", "15", "60", "240", "D"]
API_KEY = os.getenv("LLM_API_KEY") # Provider independent name
API_PROVIDER = os.getenv("LLM_PROVIDER", "openai") # openai or gemini

import google.generativeai as genai
from openai import OpenAI

def analyze_image_with_llm(image_url, ticker, interval):
    """
    Sends the image to an LLM for ICT analysis.
    """
    if not API_KEY:
        logger.warning("⚠️ No LLM_API_KEY found. Skipping analysis step.")
        return "Analysis skipped (No API Key)"

    logger.info(f"🧠 Analyzing chart for {ticker} [{interval}] with {API_PROVIDER.upper()}...")
    
    try:
        if API_PROVIDER.lower() == "gemini":
            # Gemini Implementation
            genai.configure(api_key=API_KEY)
            # Use standard Flash model (highest free compatibility)
            model = genai.GenerativeModel('gemini-flash-latest') 
            
            # Gemini typically expects image data, not just a URL (unless it's a public URL).
            import requests
            from io import BytesIO
            from PIL import Image
            
            if image_url.startswith("data:image"):
                # Handle base64
                header, encoded = image_url.split(",", 1)
                image_data = base64.b64decode(encoded)
                image = Image.open(BytesIO(image_data))
            else:
                # Handle URL
                response = requests.get(image_url)
                image = Image.open(BytesIO(response.content))
                
            response = model.generate_content([ICT_SYSTEM_PROMPT, image])
            return response.text
            
        else:
            # OpenAI Implementation - Recommending gpt-4o-mini for "unlimited" feel
            client = OpenAI(api_key=API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": ICT_SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "text", "text": f"Analyze this multi-timeframe grid chart for {ticker}."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]} 
                ]
            )
            return response.choices[0].message.content
            
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        return f"Error during analysis: {e}"

def run_analysis_cycle():
    """Runs one full cycle of analysis for all tickers and timeframes."""
    logger.info("🚀 Starting analysis cycle...")
    
    # Ensure briefs directory exists
    os.makedirs("briefs", exist_ok=True)
    
    # Scraper config
    headless = os.getenv("MCP_SCRAPER_HEADLESS", "True").lower() == "true"
    window_width = int(os.getenv("MCP_SCRAPER_WINDOW_WIDTH", "1400"))
    window_height = int(os.getenv("MCP_SCRAPER_WINDOW_HEIGHT", "1400"))
    
    # Initialize Scraper
    try:
        with TradingViewScraper(
            headless=headless,
            window_size=f"{window_width},{window_height}",
            use_save_shortcut=True 
        ) as scraper:
            
            for ticker in TICKERS:
                ticker_clean = ticker.replace(":", "_")
                brief_content = [f"# Investment Brief: {ticker}", f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
                
                # Ensure images directory exists within briefs
                img_dir = "briefs/images"
                os.makedirs(img_dir, exist_ok=True)
                
                logger.info(f"📊 Analyzing {ticker} with Grid Optimization...")
                
                images_data = [] # List of (interval, PIL.Image)
                
                # 1. Fetch and save all charts
                for interval in TIMEFRAMES:
                    try:
                        logger.info(f"  📸 Fetching chart: {ticker} [{interval}]")
                        image_url = scraper.get_chart_image_url(ticker, interval)
                        
                        if image_url:
                            # Precompute image data
                            if image_url.startswith("data:image"):
                                header, encoded = image_url.split(",", 1)
                                image_data = base64.b64decode(encoded)
                            else:
                                import requests
                                image_data = requests.get(image_url).content
                            
                            # Save individual image for the user to see clearly
                            img_filename = f"{ticker_clean}_{interval}_{timestamp}.png"
                            img_path = os.path.join(img_dir, img_filename)
                            with open(img_path, "wb") as f:
                                f.write(image_data)
                            
                            from io import BytesIO
                            from PIL import Image
                            img = Image.open(BytesIO(image_data))
                            # Keep record of both PIL image for grid and filename for the brief
                            images_data.append({
                                "interval": interval,
                                "img": img,
                                "filename": img_filename
                            })
                        else:
                            logger.error(f"  ❌ Failed to get image for {ticker} [{interval}]")
                    except Exception as e:
                        logger.error(f"  ❌ Error fetching {ticker} [{interval}]: {e}")

                if not images_data:
                    logger.error(f"  ❌ No images fetched for {ticker}. Skipping.")
                    continue

                # 2. Create Grid Image (for AI)
                total_height = sum(data["img"].size[1] for data in images_data)
                max_width = max(data["img"].size[0] for data in images_data)
                
                from PIL import Image, ImageDraw
                grid_img = Image.new('RGB', (max_width, total_height + (len(images_data) * 40)), (255, 255, 255))
                y_offset = 0
                
                for data in images_data:
                    # Draw a label
                    draw = ImageDraw.Draw(grid_img)
                    draw.text((10, y_offset + 5), f"Timeframe: {data['interval']}", fill=(0, 0, 0))
                    y_offset += 30
                    
                    grid_img.paste(data["img"], (0, y_offset))
                    y_offset += data["img"].size[1] + 10

                # 3. Save Grid Image (technical record)
                grid_filename = f"{ticker_clean}_grid_{timestamp}.png"
                grid_path = os.path.join(img_dir, grid_filename)
                grid_img.save(grid_path)
                logger.info(f"✅ Grid image saved: {grid_path}")

                # 4. Single AI Analysis (using the grid to save tokens)
                from io import BytesIO
                buffered = BytesIO()
                grid_img.save(buffered, format="PNG")
                grid_base64 = base64.b64encode(buffered.getvalue()).decode()
                grid_data_uri = f"data:image/png;base64,{grid_base64}"
                
                logger.info(f"🧠 Performing single ICT analysis on the combined grid...")
                full_analysis = analyze_image_with_llm(grid_data_uri, ticker, "Combined (5mo-D)")

                # 5. Assemble Brief (Displaying individual high-res charts for the user)
                brief_content.append(f"## Top-Down Analysis Summary")
                brief_content.append(full_analysis)
                brief_content.append("\n---\n")
                
                brief_content.append("## Detailed Timeframe Charts")
                for data in images_data:
                    brief_content.append(f"### Timeframe: {data['interval']}")
                    brief_content.append(f"![Chart {data['interval']}](images/{data['filename']})")
                    brief_content.append("")

                # Save Brief
                filename = f"briefs/Brief_{ticker_clean}_{timestamp}.md"
                with open(filename, "w") as f:
                    f.write("\n".join(brief_content))
                
                logger.info(f"✅ Brief saved: {filename}")
                        
    except Exception as e:
        logger.critical(f"🔥 Critical Scraper Error: {e}")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Analyst Bot")
    parser.add_argument("--once", action="store_true", help="Run analysis once and exit")
    parser.add_argument("--ticker", type=str, help="Specific ticker to analyze (optional)")
    args = parser.parse_args()

    if args.ticker:
        TICKERS = [args.ticker]
        logger.info(f"🎯 Targeted analysis for: {args.ticker}")

    if args.once:
        logger.info("🤖 Running single analysis cycle...")
        run_analysis_cycle()
        logger.info("✅ Done.")
    else:
        logger.info("🤖 Market Analyst Bot Initialized (Hourly Loop)")
        # Simple loop for hourly schedule
        while True:
            run_analysis_cycle()
            
            sleep_time = 3600  # 1 Hour
            logger.info(f"💤 Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
