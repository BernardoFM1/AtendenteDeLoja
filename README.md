# Atendente de Loja

Assistente virtual inteligente para atendimento automatizado em lojas e comércios via WhatsApp. O sistema utiliza uma arquitetura baseada em RAG (Retrieval-Augmented Generation), histórico de conversação em memória persistente, buffer com debounce anti-spam para mensagens fracionadas e integração com WhatsApp via Evolution API.

---

## 1. Visão Geral

O **Atendente de Loja** foi desenvolvido para solucionar desafios comuns no atendimento via WhatsApp:
- **Respostas embasadas no estoque:** Responde a dúvidas sobre disponibilidade e preços de produtos exclusivamente a partir de documentos oficiais cadastrados (PDFs/TXTs de catálogo de produtos).
- **Tratamento de mensagens consecutivas (Debounce):** Clientes frequentemente enviam mensagens fragmentadas em sequência (ex.: *"Olá"*, *"vocês tem tal produto?"*, *"qual o preço?"*). O sistema utiliza um buffer Redis com janela de espera (debounce) para consolidar essas frases em um único contexto antes de acionar a inteligência artificial.
- **Memória de conversação contextual:** Mantém o histórico de cada cliente no Redis, permitindo que o modelo compreenda referências a mensagens anteriores.
- **Guardrails de segurança:** Regras estritas nos prompts de sistema impedem vazamento de instruções internas (*prompt injection*) e alucinações sobre itens fora do catálogo.

---

## 2. Arquitetura do Sistema

```mermaid
flowchart TB
    subgraph Cliente["Canal de Comunicação"]
        User["Cliente (WhatsApp)"]
    end

    subgraph Gateway["Gateway WhatsApp"]
        EvoAPI["Evolution API (Porta 8080)"]
        Postgres[("PostgreSQL (Estado Evolution)")]
        EvoAPI <--> Postgres
    end

    subgraph Backend["Aplicação Central (FastAPI / LangChain)"]
        Webhook["POST /webhook (src.api.webhook)"]
        Buffer["Buffer de Mensagens + Debounce (src.core.buffer)"]
        RAGChain["Conversational RAG Chain (src.rag.chains)"]
        Prompts["Prompts & Guardrails (src.rag.prompts)"]
        EvoService["Evolution Service (src.services.evolution)"]
    end

    subgraph Armazenamento["Persistência & Conhecimento"]
        Redis[("Redis (Porta 6379)\n- Buffer de Mensagens\n- Memória de Sessões")]
        Chroma[("ChromaDB\n(Vectorstore Vetorial)")]
        Docs["Documentos de Catálogo (rag_files/)"]
    end

    subgraph LLMProvider["Provedor de IA"]
        OpenAI["OpenAI API\n- Embeddings: text-embedding-3-small\n- Chat: GPT-4o-mini"]
    end

    User <-->|Mensagens WhatsApp| EvoAPI
    EvoAPI -->|Webhook POST /webhook| Webhook
    Webhook --> Buffer
    Buffer <-->|Armazena/Consolida Mensagens| Redis
    Buffer -->|Dispara após Debounce| RAGChain
    RAGChain <-->|Histórico da Sessão| Redis
    RAGChain <-->|Busca Semântica| Chroma
    Docs -->|Ingestão & Chunks| Chroma
    Chroma <-->|Embeddings| OpenAI
    RAGChain <-->|Geração Aumentada| OpenAI
    RAGChain --> Prompts
    RAGChain -->|Resposta Gerada| EvoService
    EvoService -->|POST /message/sendText| EvoAPI
```

---

## 3. Fluxo de Processamento de Mensagens

```mermaid
sequenceDiagram
    autonumber
    actor Cliente as Cliente (WhatsApp)
    participant Evo as Evolution API
    participant API as FastAPI (/webhook)
    participant Red as Redis (Buffer & Memory)
    participant Core as Buffer Worker (Debounce)
    participant RAG as LangChain RAG
    participant Chroma as ChromaDB
    participant AI as OpenAI (GPT-4o-mini)

    Cliente->>Evo: Envia mensagem 1: "Olá"
    Evo->>API: POST /webhook (chat_id, "Olá")
    API->>Red: RPUSH buffer:{chat_id} "Olá"
    API->>Core: Inicia timer de Debounce (10s)

    Cliente->>Evo: Envia mensagem 2: "Tem o item X disponível?"
    Evo->>API: POST /webhook (chat_id, "Tem o item X disponível?")
    API->>Red: RPUSH buffer:{chat_id} "Tem o item X disponível?"
    API->>Core: Cancela timer anterior e reinicia timer (10s)

    Note over Core: Passam-se 10 segundos sem novas mensagens...

    Core->>Red: LRANGE buffer:{chat_id} (Consolida texto)
    Red-->>Core: Retorna texto unificado
    Core->>Red: DEL buffer:{chat_id}

    Core->>RAG: Executa pipeline conversacional
    RAG->>Red: Busca histórico da sessão (session_id = chat_id)
    RAG->>AI: Contextualiza pergunta independente com histórico
    AI-->>RAG: Pergunta contextualizada
    RAG->>Chroma: Busca trechos relevantes de produtos e preços no catálogo
    Chroma-->>RAG: Retorna produtos recuperados
    RAG->>AI: Gera resposta final com prompt do sistema e contexto RAG
    AI-->>RAG: Resposta formatada com opções e valores
    RAG->>Red: Salva interação no histórico

    RAG->>Evo: POST /message/sendText/{instance} (texto da resposta)
    Evo->>Cliente: Entrega resposta no WhatsApp
```

---

## 4. Estrutura do Projeto

O código-fonte foi estruturado de forma modular dentro do pacote `src/`, mantendo arquivos de configuração na raiz:

```text
AtendenteDeLoja/
├── .env.example               # Modelo de variáveis de ambiente
├── .gitignore                  # Regras de exclusão do Git (ignora .env, venvs, bancos)
├── Dockerfile                  # Imagem Docker da aplicação Python (FastAPI)
├── docker-compose.yml          # Orquestração (Evolution API, Postgres, Redis, Bot)
├── requirements.txt            # Dependências Python do projeto
├── README.md                   # Documentação detalhada da arquitetura e execução
├── rag_files/                  # Diretório para arquivos de catálogo (PDF/TXT)
│   └── .gitkeep                # Mantém o diretório versionado
├── vectorstore_data/           # Diretório de persistência do ChromaDB (SQLite + embeddings)
└── src/                        # Código-fonte principal modularizado
    ├── __init__.py
    ├── main.py                 # Criação e inicialização da aplicação FastAPI
    ├── config.py               # Leitura centralizada de variáveis de ambiente (.env)
    ├── api/                    # Rotas e controladores da API
    │   ├── __init__.py
    │   └── webhook.py          # Recebimento de mensagens da Evolution API
    ├── core/                   # Lógica de negócio e orquestração
    │   ├── __init__.py
    │   └── buffer.py           # Gerenciamento de buffer e debounce com Redis
    ├── rag/                    # Subsistema de Recuperação e Geração Aumentada (RAG)
    │   ├── __init__.py
    │   ├── chains.py           # Montagem das chains conversacionais do LangChain
    │   ├── memory.py           # Gestão de histórico de conversação via Redis
    │   ├── prompts.py          # Templates de prompt, identidade e guardrails
    │   └── vectorstore.py      # Ingestão de arquivos e interface com ChromaDB
    └── services/               # Clientes e integrações externas
        ├── __init__.py
        └── evolution.py        # Envio de mensagens para a Evolution API (WhatsApp)
```

---

## 5. Módulos e Componentes

### 5.1. `src/api/webhook.py`
Define a rota `POST /webhook` responsável por receber os disparos da Evolution API. O endpoint:
- Valida o payload JSON recebido.
- Extrai o identificador do remetente (`remoteJid`) e o conteúdo do texto (`conversation`).
- Descarta mensagens originadas em grupos do WhatsApp (sufixo `@g.us`).
- Encaminha mensagens individuais válidas para o buffer assíncrono.

### 5.2. `src/core/buffer.py`
Implementa a estratégia de agrupamento de mensagens consecutivas:
- Armazena as mensagens em uma lista no Redis associada à chave `${chat_id}_msg_buffer`.
- Define um TTL padrão de 300 segundos para o buffer.
- Gerencia uma tarefa assíncrona (`asyncio.Task`) por cliente. Sempre que uma nova mensagem chega antes do tempo estipulado (`DEBOUNCE_SECONDS`), a tarefa em andamento é cancelada e reiniciada.
- Ao atingir o tempo sem interrupções, consolida todas as mensagens em uma única string e invoca a cadeia RAG.

### 5.3. `src/rag/`
- **`vectorstore.py`:** Monitora o diretório `rag_files/`. Arquivos PDF e TXT são carregados com `PyPDFLoader` ou `TextLoader`, fragmentados via `RecursiveCharacterTextSplitter` (chunk de 1000 caracteres, sobreposição de 200) e indexados no ChromaDB utilizando `OpenAIEmbeddings`. Os arquivos processados são automaticamente movidos para `rag_files/processed/`.
- **`memory.py`:** Utiliza `RedisChatMessageHistory` para guardar o histórico das mensagens de cada usuário, identificado pelo seu número de WhatsApp (`session_id = chat_id`).
- **`prompts.py`:** Centraliza os prompts do sistema:
  - *Contextualização:* Reformula perguntas que dependem do histórico em perguntas independentes para busca no vetor.
  - *Identidade e Atendimento:* Estabelece o tom profissional de atendente de loja, consulta obrigatória ao catálogo, formatação de preços e oferta de carrinho.
  - *Guardrails de Segurança:* Bloqueia tentativas de injeção de instruções e veda respostas sobre informações inexistentes no catálogo.
- **`chains.py`:** Une o modelo `ChatOpenAI`, o retriever vetorial, os prompts e a memória Redis através de `create_history_aware_retriever`, `create_stuff_documents_chain` e `RunnableWithMessageHistory`.

### 5.4. `src/services/evolution.py`
Cliente HTTP simples e robusto baseado na biblioteca `requests` que realiza a chamada autenticada via API Key para o endpoint `/message/sendText/{instance}` da Evolution API.

---

## 6. Configuração e Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto baseado no arquivo `.env.example`:

```bash
cp .env.example .env
```

| Variável | Descrição | Exemplo / Padrão |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | Chave de API da OpenAI para geração e embeddings | `sk-proj-...` |
| `OPENAI_MODEL_NAME` | Modelo de chat da OpenAI | `gpt-4o-mini-2024-07-18` |
| `OPENAI_MODEL_TEMPERATURE` | Temperatura de geração do modelo | `0` |
| `EVOLUTION_API_URL` | URL base da Evolution API | `http://evolution-api:8080` |
| `EVOLUTION_INSTANCE_NAME` | Nome da instância criada no WhatsApp | `Business` |
| `AUTHENTICATION_API_KEY` | Chave global de autenticação da Evolution API | `SuaChaveSegura` |
| `CONFIG_SESSION_PHONE_VERSION` | Versão da sessão do WhatsApp Web | `2.3000.1015901307` |
| `CACHE_REDIS_URI` | URL de conexão com a instância Redis | `redis://redis:6379/6` |
| `BUFFER_KEY_SUFIX` | Sufixo da chave do Redis para o buffer de mensagens | `_msg_buffer` |
| `DEBOUNCE_SECONDS` | Tempo em segundos de inatividade para disparar a IA | `10` |
| `BUFFER_TTL` | Tempo de vida do buffer no Redis em segundos | `300` |
| `VECTOR_STORE_PATH` | Diretório de persistência do ChromaDB | `vectorstore` |
| `RAG_FILES_DIR` | Diretório de arquivos de documentos para o RAG | `rag_files` |
| `DATABASE_CONNECTION_URI` | Conexão com PostgreSQL da Evolution API | `postgresql://postgres:postgres@postgres:5432/evolution?schema=public` |

---

## 7. Como Executar

### 7.1. Execução com Docker Compose (Recomendado)

O arquivo `docker-compose.yml` provisiona todos os quatro serviços necessários:

```bash
# 1. Configure suas credenciais no arquivo .env
cp .env.example .env

# 2. Suba todos os containers em segundo plano
docker compose up -d --build

# 3. Verifique o status dos serviços
docker compose ps
```

Serviços iniciados:
- **Evolution API:** `http://localhost:8080`
- **PostgreSQL:** `localhost:5432`
- **Redis:** `localhost:6379`
- **Bot (FastAPI):** `http://localhost:8000`

### 7.2. Configuração do Webhook na Evolution API

Após inicializar a Evolution API e conectar o WhatsApp via QR Code:
1. Acesse as configurações da instância criada na Evolution API.
2. Defina a URL do Webhook de mensagens para:
   ```text
   http://bot:8000/webhook
   ```
   *(Caso execute a Evolution API fora do Docker Compose, utilize o endereço IP ou domínio onde a porta 8000 está acessível).*
3. Habilite o evento `MESSAGES_UPSERT`.

### 7.3. Execução Local para Desenvolvimento

Caso prefira rodar a aplicação Python fora de containers:

```bash
# 1. Crie e ative um ambiente virtual
python -m venv .venv
# No Linux/macOS:
source .venv/bin/activate
# No Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Inicie os serviços auxiliares (Redis, Postgres, Evolution API) via Docker
docker compose up -d redis postgres evolution-api

# 4. Ajuste no .env as URLs para localhost:
# CACHE_REDIS_URI=redis://localhost:6379/6
# EVOLUTION_API_URL=http://localhost:8080

# 5. Execute o servidor de desenvolvimento
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 8. Ingestão de Documentos no RAG

Para atualizar ou adicionar produtos e tabelas de preços:
1. Deposite os arquivos `.pdf` ou `.txt` dentro do diretório `rag_files/`.
2. Ao receber a primeira mensagem ou ao inicializar o vetor, a função `load_documents()` processa automaticamente os novos arquivos, divide-os em chunks, indexa no ChromaDB e transfere os arquivos originais para `rag_files/processed/`.

---

## 9. Endpoints da Aplicação

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `POST` | `/webhook` | Recebe notificações de novas mensagens da Evolution API |
| `GET` | `/health` | Checagem de integridade do serviço FastAPI |
| `GET` | `/docs` | Documentação interativa Swagger/OpenAPI |
| `GET` | `/redoc` | Documentação alternativa ReDoc |

---

## 10. Segurança

- **Chaves de API:** Nunca versione arquivos `.env` ou inclua chaves da OpenAI diretamente no código ou histórico do Git.
- **Git Ignore:** O arquivo `.gitignore` configurado neste projeto garante a exclusão de arquivos de ambiente, caches `__pycache__`, bases de dados locais SQLite (`*.sqlite3`) e diretórios de ambientes virtuais (`venv/`, `venvv/`).
- **Guardrails:** As instruções em `src/rag/prompts.py` bloqueiam respostas baseadas em conhecimento externo ao catálogo da loja e rejeitam comandos para revelar regras de sistema.
