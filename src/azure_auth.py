import os
from datetime import datetime, timedelta
from azure.identity import CertificateCredential
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set proxy environment variables if configured in .env
if os.getenv("HTTP_PROXY"):
    os.environ["http_proxy"] = os.getenv("HTTP_PROXY")
if os.getenv("HTTPS_PROXY"):
    os.environ["https_proxy"] = os.getenv("HTTPS_PROXY")
if os.getenv("NO_PROXY"):
    os.environ["no_proxy"] = os.getenv("NO_PROXY")

# Global variables for token management
access_token = None
token_expiration = None

def get_access_token():
    """Authenticate and return a valid access token."""
    global access_token, token_expiration
    if access_token is None or datetime.now() >= token_expiration:
        cert_path = "./cert/apim-exp.pem"
        scope = "https://cognitiveservices.azure.com/.default"
        credential = CertificateCredential(
            client_id=os.environ["AZURE_SPN_CLIENT_ID"],
            certificate_path=cert_path,
            tenant_id=os.environ["AZURE_TENANT_ID"],
            scope=scope,
            logging_enable=False
        )
        token_response = credential.get_token(scope)
        access_token = token_response.token
        token_expiration = datetime.now() + timedelta(seconds=token_response.expires_on - datetime.now().timestamp())
    return access_token

def setup_azure_openai_client():
    """Set up the Azure OpenAI client using the acquired token."""
    token = get_access_token()
    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        default_headers={
            "Authorization": f"Bearer {token}",
            "user-sid": os.getenv("USER_SID", ""),
        }
    )
    return client