from fastapi import FastAPI
from src.api.webhook import router as webhook_router

app = FastAPI(
    title="Atendente de Loja",
    description="Assistente Virtual de Loja com RAG para WhatsApp",
    version="1.0.0",
)

# Registra as rotas da aplicação
app.include_router(webhook_router)

@app.get("/health")
async def health_check():
    """Endpoint de verificação de integridade da aplicação."""
    return {"status": "healthy", "service": "Atendente de Loja"}
