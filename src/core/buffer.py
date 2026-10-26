import asyncio
import logging
from collections import defaultdict
from typing import Dict

import redis.asyncio as redis

from src.config import REDIS_URL, BUFFER_KEY_SUFIX, DEBOUNCE_SECONDS, BUFFER_TTL
from src.services.evolution import send_whatsapp_message
from src.rag.chains import get_conversational_rag_chain

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
debounce_tasks: Dict[str, asyncio.Task] = defaultdict(asyncio.Task)

def log(*args):
    print("[BUFFER]", *args)

async def buffer_message(chat_id: str, message: str) -> None:
    """
    Adiciona a mensagem recebida ao buffer do Redis com TTL
    e reinicia o temporizador de debounce para o chat_id correspondente.
    """
    buffer_key = f"{chat_id}{BUFFER_KEY_SUFIX}"

    await redis_client.rpush(buffer_key, message)
    await redis_client.expire(buffer_key, BUFFER_TTL)

    log(f"Mensagem adicionada ao buffer de {chat_id}: {message}")

    # Reinicia o temporizador se já houver uma contagem ativa para o chat
    if debounce_tasks.get(chat_id):
        debounce_tasks[chat_id].cancel()
        log(f"Debounce resetado para {chat_id}")

    debounce_tasks[chat_id] = asyncio.create_task(handle_debounce(chat_id))

async def handle_debounce(chat_id: str) -> None:
    """
    Aguarda o tempo de debounce (inatividade). Se não houver novas mensagens,
    agrupa o texto acumulado, executa a cadeia RAG e envia a resposta via WhatsApp.
    """
    try:
        log(f"Iniciando debounce ({DEBOUNCE_SECONDS}s) para {chat_id}")
        await asyncio.sleep(float(DEBOUNCE_SECONDS))

        buffer_key = f"{chat_id}{BUFFER_KEY_SUFIX}"
        messages = await redis_client.lrange(buffer_key, 0, -1)

        full_message = " ".join(messages).strip()
        log(f"Mensagem consolidada para {chat_id}: {full_message}")

        if full_message:
            log(f"Executando RAG para {chat_id}...")
            conversational_rag_chain = get_conversational_rag_chain()
            response = conversational_rag_chain.invoke(
                input={"input": full_message},
                config={"configurable": {"session_id": chat_id}},
            )
            ai_response = response.get("answer", "")

            log(f"Enviando resposta via WhatsApp para {chat_id}")
            send_whatsapp_message(
                number=chat_id,
                text=ai_response,
            )

        await redis_client.delete(buffer_key)

    except asyncio.CancelledError:
        log(f"Debounce cancelado para {chat_id} (nova mensagem chegou)")
    except Exception as exc:
        logger.error("Erro no processamento do debounce para %s: %s", chat_id, exc)
