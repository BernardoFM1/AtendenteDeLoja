import logging
import requests
from src.config import (
    EVOLUTION_API_URL,
    EVOLUTION_INSTANCE_NAME,
    EVOLUTION_AUTHENTICATION_API_KEY,
)

logger = logging.getLogger(__name__)

def send_whatsapp_message(number: str, text: str) -> bool:
    """Envia uma mensagem de texto no WhatsApp através da Evolution API."""
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
    headers = {
        "apikey": EVOLUTION_AUTHENTICATION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "number": number,
        "text": text,
    }

    try:
        response = requests.post(
            url=url,
            json=payload,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Erro ao enviar mensagem WhatsApp para %s: %s", number, exc)
        return False
