import os

from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.environ.get("OPENAI_API_KEY")
mongo_uri = os.environ.get("MONGO_URI")
gupshup_app_id = os.environ.get("GUPSHUP_APP_ID")
gupshup_token = os.environ.get("GUPSHUP_TOKEN")
gupshup_app_name = os.environ.get("GUPSHUP_APP_NAME")
gupshup_api_key = os.environ.get("GUPSHUP_API_KEY")
pinecone_api = os.environ.get("PINECONE_API")
pinecone_namespace = os.environ.get("PINECONE_NAMESPACE")
webhook_api = os.environ.get("WEBHOOK_API")

def _normalize_private_key(raw_key: str) -> str:
    """Normalize a PEM private key regardless of how it was pasted into env vars."""
    key = raw_key.strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in ("'", '"'):
        key = key[1:-1]
    if "\\n" in key and "\n" not in key:
        key = key.replace("\\n", "\n")
    return key.strip() + "\n"


google_private_key_id = os.environ.get("GOOGLE_PRIVATE_KEY_ID")
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_private_key = _normalize_private_key(os.environ.get("GOOGLE_PRIVATE_KEY", ""))
google_client_email = os.environ.get("GOOGLE_CLIENT_EMAIL")
google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
google_client_x509_cert_url = os.environ.get("GOOGLE_CLIENT_X509_CERT_URL")

qlink_app_id = os.environ.get("QLINK_APP_ID")
qlink_app_name = os.environ.get("QLINK_APP_NAME")
qlink_token = os.environ.get("QLINK_TOKEN")

username = os.environ.get("LOGIN_USERNAME")
password = os.environ.get("LOGIN_PASS")

futwork_webhook = os.environ.get("FUTWORKS_API")
futwork_pacific_agent = os.environ.get("FUTWORK_PACIFIC_AGENT")

fist_awards_template_id = os.environ.get("FIST_AWARDS_TEMPLATE_ID")
fist_awards_template_id_v2 = os.environ.get("FIST_AWARDS_TEMPLATE_ID_V2")
fist_awards_template_id_v3 = os.environ.get("FIST_AWARDS_TEMPLATE_ID_V3")
fist_awards_template_id_v4 = os.environ.get("FIST_AWARDS_TEMPLATE_ID_V4")