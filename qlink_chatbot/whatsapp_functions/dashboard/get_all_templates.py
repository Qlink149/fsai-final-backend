import httpx

from qlink_chatbot.utils.env_load import gupshup_app_id, gupshup_token
from qlink_chatbot.utils.logger_config import logger


def get_all_templates():
    """Get all templates."""
    logger.info(
        "Get All Templates"
    )
    url = f"https://partner.gupshup.io/partner/app/{gupshup_app_id}/templates"
    headers = {
        "Authorization": f"{gupshup_token}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.get(url, headers=headers)
        data = response.json()

        if data.get("status") == "success":
            return data.get("templates", [])
        else:
            logger.info("Response error for all templates", extra={"response": data})
            return None

    except Exception as e:
        logger.error("Error in sending spot booking flow", extra={"error": e})
        raise e
    