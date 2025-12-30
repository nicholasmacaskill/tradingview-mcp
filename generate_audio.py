import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("LLM_API_KEY_OPENAI") or os.getenv("OPENAI_API_KEY")

if not api_key:
    print("Error: OPENAI_API_KEY not found. Please set it in your .env file.")
    sys.exit(1)

client = OpenAI(api_key=api_key)

voice_script = "Listen to me. We are selling everything. The price is {price}. Hit the bid. I don't care what it is, just sell it."

def generate_voice(price):
    text = voice_script.format(price=price)
    response = client.audio.speech.create(
        model="tts-1",
        voice="onyx", # "Onyx" is the closest to a deep, authoritative Kevin Spacey / Sam Rogers tone
        input=text
    )
    
    output_path = "alert_message.mp3"
    response.stream_to_file(output_path)
    print(f"Generated: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        price_arg = sys.argv[1]
    else:
        price_arg = "90000"
        
    generate_voice(price_arg)
