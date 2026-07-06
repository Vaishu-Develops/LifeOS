import os
from dotenv import load_dotenv
from lifeos.mcp import oauth

# Load environment variables from .env
load_dotenv()

client_secrets_file = os.getenv("LIFEOS_OAUTH_CLIENT_SECRET_FILE")
if not client_secrets_file:
    print("Error: LIFEOS_OAUTH_CLIENT_SECRET_FILE not found in .env")
    exit(1)

# We need full access to Calendar and Gmail for the app to function properly
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://mail.google.com/"
]

print("Starting Google Login...")
# Build the OAuth flow
flow = oauth.build_flow(client_secrets_file, SCOPES)

# This will open a browser window and ask for permission
creds = flow.run_local_server(port=0)

# Save the credentials to tokens.json so the Streamlit app can find them
oauth.save_tokens(creds)
print("\nSuccess! Tokens saved securely. You can now go back to the Streamlit app and click 'Sign In with Google'.")
