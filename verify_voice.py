import time
from monitor_price import trigger_notification, logger

logger.info("Starting AI Voice Verification...")
trigger_notification(90123.45, "BTCUSDT", "Voice Verification Test")

# Keep alive to allow thread to finish and subprocess to play
time.sleep(10)
logger.info("Verification Complete.")
