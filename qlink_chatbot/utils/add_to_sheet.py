from datetime import datetime

import gspread
import pytz
from google.oauth2.service_account import Credentials

from qlink_chatbot.utils.env_load import (
    google_client_email,
    google_client_id,
    google_client_x509_cert_url,
    google_private_key,
    google_private_key_id,
    google_project_id,
)
from qlink_chatbot.utils.logger_config import logger

IST = pytz.timezone("Asia/Kolkata")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = "1gxyApjYoyepIXpSeUGrH4UNm7lcNXxojN3qUvKVf-LE"

SHEET_NAME = "Sheet1"

credentials = Credentials.from_service_account_info(
    {
        "type": "service_account",
        "project_id": google_project_id,
        "private_key_id": google_private_key_id,
        "private_key": google_private_key,
        "client_email": google_client_email,
        "client_id": google_client_id,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": google_client_x509_cert_url,
        "universe_domain": "googleapis.com"
    },
    scopes=SCOPES
)
client = gspread.authorize(credentials)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)



def add_data_to_sheet(data: dict):
    """Append a new lead entry to Google Sheet."""
    try:
        row = [
            datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            data.get("username", ""),
            data.get("question", ""),
            data.get("wa_phone", "")
        ]
        sheet.append_row(row)
        logger.info("Lead added to Google Sheet", extra={"lead": row})
    except Exception as e:
        logger.error("Failed to add lead to Google Sheet", extra={"error": str(e)})
        raise e 
    
