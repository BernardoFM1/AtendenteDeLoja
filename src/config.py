import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

# Configurações OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini-2024-07-18")
OPENAI_MODEL_TEMPERATURE = float(os.getenv("OPENAI_MODEL_TEMPERATURE", "0"))

# Prompts
AI_CONTEXTUALIZE_PROMPT = os.getenv("AI_CONTEXTUALIZE_PROMPT")
AI_SYSTEM_PROMPT = os.getenv("AI_SYSTEM_PROMPT")

# Configurações Evolution API (WhatsApp)
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://evolution-api:8080")
EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME", "Business")
EVOLUTION_AUTHENTICATION_API_KEY = os.getenv("AUTHENTICATION_API_KEY")

# Caminhos RAG e ChromaDB
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "vectorstore")
RAG_FILES_DIR = os.getenv("RAG_FILES_DIR", "rag_files")

# Configurações Redis e Buffer
REDIS_URL = os.getenv("CACHE_REDIS_URI", "redis://redis:6379/6")
BUFFER_KEY_SUFIX = os.getenv("BUFFER_KEY_SUFIX", "_msg_buffer")
DEBOUNCE_SECONDS = float(os.getenv("DEBOUNCE_SECONDS", "10"))
BUFFER_TTL = int(os.getenv("BUFFER_TTL", "300"))
