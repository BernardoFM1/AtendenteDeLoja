from fastapi import APIRouter, Request
from src.core.buffer import buffer_message

router = APIRouter()

@router.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint de webhook para receber mensagens da Evolution API.
    Filtra mensagens inválidas ou de grupo e repassa para o buffer com debounce.
    """
    data = await request.json()
    message_data = data.get("data", {})
    key_data = message_data.get("key", {})
    
    chat_id = key_data.get("remoteJid")
    message_content = message_data.get("message", {}).get("conversation")

    # Ignora mensagens de grupos (@g.us) e mensagens vazias
    if chat_id and message_content and not chat_id.endswith("@g.us"):
        await buffer_message(
            chat_id=chat_id,
            message=message_content,
        )

    return {"status": "ok"}
