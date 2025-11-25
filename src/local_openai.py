import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_local_openai_client():
    """Set up the standard OpenAI client for local development."""
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"]
    )
    return client
