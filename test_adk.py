import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.DEBUG)

from lifeos.agents.adk_wrapper import ADKClient

client = ADKClient()
print("Has Gemini?", client._has_gemini)
if not client._has_gemini:
    print("API Key in env:", bool(os.getenv("GEMINI_API_KEY")))

print("Intent:", client.classify_intent("I need to remember to buy eggs and milk tomorrow"))
print("Intent:", client.classify_intent("Are there any new emails?"))
