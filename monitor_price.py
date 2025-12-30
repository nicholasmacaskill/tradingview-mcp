import time
import argparse
import logging
import subprocess
import os
import threading
from openai import OpenAI
from dotenv import load_dotenv
from tview_scraper import TradingViewScraper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure OpenAI
api_key = os.getenv("LLM_API_KEY_OPENAI") or os.getenv("OPENAI_API_KEY")
client = None
if api_key:
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to init OpenAI client: {e}")

def play_ai_voice(price):
    """Generates and plays AI voice, falling back to system voice on error."""
    text = f"Listen to me. We are selling everything. The price is {price}. Hit the bid. I don't care what it is, just sell it."

    if client:
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=text
            )
            
            # Save to temp file
            output_path = "/tmp/margin_call_alert.mp3"
            response.stream_to_file(output_path)
            
            # Play audio
            subprocess.run(["afplay", output_path])
            return
            
        except Exception as e:
            logger.error(f"AI Voice Generation Failed: {e}. Falling back to system voice.")
            # Fall through to system voice

    # Fallback to system voice
    subprocess.Popen(["say", "-v", "Samantha", "-r", "150", text])

def trigger_notification(price, ticker, message="Target Reached!"):
    """Triggers a Mac terminal alert with a Margin Call style voice."""
    logger.info(f"🔔 ALERT: {ticker} at {price}")
    
    # 2. Audio Alert (AI Voice - Kevin Spacey Style)
    # Run in thread to avoid blocking visual alert while generating audio
    if client:
        threading.Thread(target=play_ai_voice, args=(price,)).start()
    else:
        # Fallback to system voice if no API key
        speech = f"Listen to me. We are selling everything. The price is {price}. Hit the bid."
        subprocess.Popen(["say", "-v", "Kevin", "-r", "150", speech])

    # 1. Visual Alert (Standard Notification Banner)
    # "display notification" is the standard banner style ("like any other app")
    try:
        cmd_visual = f'display notification "Price: {price}\n{message}" with title "🚨 MARGIN CALL: {ticker}"'
        subprocess.run(["osascript", "-e", cmd_visual])
    except Exception:
        pass

def monitor_loop(ticker, min_price, max_price, interval=30):
    logger.info(f"👀 Starting monitor for {ticker}. Target Zone: {min_price} - {max_price}")
    
    with TradingViewScraper(headless=True) as scraper:
        while True:
            try:
                price = scraper.get_current_price(ticker)
                
                if price:
                    logger.info(f"💰 Current Price: {price}")
                    
                    if min_price <= price <= max_price:
                        trigger_notification(price, ticker, "Inside Entry Zone!")
                        # Optional: Break after alert? Or keep alerting?
                        # For now, we'll sleep longer to avoid spamming
                        time.sleep(60) 
                    
                else:
                    logger.warning("⚠️ Could not fetch price.")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitor stopped by user.")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitor loop: {e}")
                time.sleep(10) # Wait before retry

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", type=str, default="BYBIT:BTCUSDT.P")
    parser.add_argument("--min", type=float, required=True)
    parser.add_argument("--max", type=float, required=True)
    args = parser.parse_args()

    monitor_loop(args.ticker, args.min, args.max)
