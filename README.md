<<<<<<< HEAD
# 🗼 O-RAN Digital Twin — Knowledge Assistant

> A **Retrieval-Augmented Generation (RAG)** assistant for **O-RAN technical documentation**. Ask questions in natural language and get accurate, **source-grounded** answers drawn only from the indexed documents — no hallucination.

<p>
<img alt="Python" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
<img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white">
<img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
<img alt="Qdrant" src="https://img.shields.io/badge/Qdrant-Vector%20DB-DC244C">
<img alt="LlamaIndex" src="https://img.shields.io/badge/LlamaIndex-Workflows-8A2BE2">
</p>

---

## 📖 Overview

This project indexes O-RAN technical documents into a vector database, then answers user questions through a **two-stage retrieval pipeline** (fast dense retrieval + precise cross-encoder reranking) followed by a large language model that is **constrained to answer only from the retrieved context**. The result is a chat assistant that gives traceable, document-backed answers — and explicitly says when the answer isn't in its sources.

It is fully **containerized** (Docker Compose) and ships with a clean Streamlit chat UI.

---

## ✨ Key Features

- 🔎 **Two-stage retrieval** — dense vector search (recall) + cross-encoder reranking (precision)
- 🧷 **Strict grounding** — answers come only from retrieved sources; refuses out-of-scope questions instead of guessing
- 🧩 **Local embeddings & reranking** — runs on your machine; only generation is hosted
- 🗂️ **Source attribution** — every answer lists the documents it was built from
- ⚡ **Idempotent ingestion** — documents are embedded once; restarts are instant
- 🐳 **One-command deploy** — `docker compose up`

---

## 🏗️ Architecture

```mermaid
flowchart LR
    U["👤 User"] -->|":8501"| GUI["🖥️ Streamlit UI<br/>rag-gui"]
    GUI -->|"POST /api/v1/query :8000"| API["⚙️ FastAPI Core<br/>rag-core-api"]
    API -->|"embed + search"| QD[("🧠 Qdrant<br/>Vector DB")]
    API -->|"generate"| GEM["✨ Gemini 2.5 Flash<br/>(Google API)"]

    classDef ui fill:#00D2FF,stroke:#0077aa,color:#001018,font-weight:bold
    classDef core fill:#FFB454,stroke:#b3701f,color:#1a1a1a,font-weight:bold
    classDef db fill:#DC244C,stroke:#7a1029,color:#fff,font-weight:bold
    classDef ext fill:#8A2BE2,stroke:#4b0f86,color:#fff,font-weight:bold
    class GUI ui
    class API core
    class QD db
    class GEM ext
```

---

## 🔁 RAG Pipeline

```mermaid
flowchart TB
    subgraph ING["📥 Ingestion (once)"]
        direction LR
        P["📄 Documents"] --> S["✂️ Chunk<br/>SentenceSplitter<br/>512 / 64"] --> E1["🔢 Embed<br/>BGE-large"] --> Q1[("Qdrant<br/>upsert")]
    end

    subgraph QRY["💬 Query (per request)"]
        direction LR
        Qn["❓ Question"] --> E2["🔢 Embed query"] --> R["🔎 Retrieve<br/>top-20"] --> RK["🎯 Rerank<br/>cross-encoder → top-5"] --> CTX["🧱 Build context<br/>+ sources"] --> LLM["✨ Gemini<br/>grounded prompt"] --> ANS["✅ Answer + sources"]
    end

    Q1 -.->|"indexed vectors"| R

    classDef ing fill:#0E7C66,stroke:#063f33,color:#fff
    classDef qry fill:#1E5AAE,stroke:#0d2b55,color:#fff
    class P,S,E1,Q1 ing
    class Qn,E2,R,RK,CTX,LLM,ANS qry
```

---

## 🔄 Request Sequence

```mermaid
sequenceDiagram
    actor User
    participant GUI as Streamlit
    participant API as FastAPI
    participant QD as Qdrant
    participant RR as Reranker
    participant GEM as Gemini

    User->>GUI: Ask a question
    GUI->>API: POST /api/v1/query
    API->>API: Embed query (BGE-large)
    API->>QD: Vector search (top-20)
    QD-->>API: Candidate chunks
    API->>RR: Rerank → top-5
    API->>GEM: Context + question (grounded prompt)
    GEM-->>API: Source-grounded answer
    API-->>GUI: { response, sources }
    GUI-->>User: Answer + source list
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **UI** | Streamlit |
| **API** | FastAPI + Uvicorn |
| **Orchestration** | LlamaIndex Workflows (event-driven) |
| **Embeddings** | `BAAI/bge-large-en-v1.5` (1024-d, local) |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` (local) |
| **LLM** | Google Gemini 2.5 Flash |
| **Vector DB** | Qdrant (HNSW, cosine) |
| **Packaging** | Docker + Docker Compose |

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- A **Google AI Studio API key** (for Gemini)

### 1. Configure environment

Create a `.env` file in the project root (see `.env.example`):

```env
QDRANT_HOST=qdrant-db
QDRANT_PORT=6333
COLLECTION_NAME=oran_digital_twin

GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

> ⚠️ Never commit your real API key to GitHub.
> Keep the `.env` file private and ensure it is included in `.gitignore`.

### 2. Add your documents
Place PDFs / Markdown / text files in:
```
data/source_docs/
```

### 3. Launch
```bash
docker compose up -d --build
```

First boot embeds your documents (a few minutes). Watch progress:
```bash
docker compose logs -f rag-core-api
```
Wait for `Application startup complete`.

### 4. Open the app
| Service | URL |
|---|---|
| 🖥️ Chat UI | http://localhost:8501 |
| 📚 API docs | http://localhost:8000/docs |

---

## 🔌 API

**`POST /api/v1/query`**
```json
// request
{ "query": "How is handover managed across Non-RT and Near-RT RIC?" }
```
```json
// response
{
  "query": "...",
  "response": "Source-grounded answer ...",
  "sources": "[1] document.pdf\n[2] document.pdf"
}
```

**`GET /health`** → `{ "status": "healthy" }`

---

## 📁 Project Structure

```
.
├── api/
│   └── main.py              # FastAPI app + endpoints
├── config/
│   └── settings.py          # Central configuration (Pydantic)
├── services/
│   ├── ingestion.py         # Chunk → embed → store (idempotent)
│   ├── pipeline.py          # Retrieve → rerank → generate
│   └── prompt_templates.py
├── gui/
│   └── app.py               # Streamlit chat UI
├── data/source_docs/        # Your documents go here
├── docker/
│   ├── Dockerfile.api
│   └── entrypoint.sh        # Waits for Qdrant, then starts API
├── docker-compose.yml
└── requirements.txt
```

---

## 🧠 How It Works

1. **Ingestion** — documents are split into ~512-token overlapping chunks, embedded with BGE-large, and stored in Qdrant. This runs once; subsequent restarts skip it.
2. **Retrieval** — the query is embedded and matched against stored vectors to recall the top 20 candidates.
3. **Reranking** — a cross-encoder re-scores each (query, chunk) pair jointly and keeps the 5 most relevant.
4. **Generation** — the selected context is injected into a prompt that instructs Gemini to answer **only** from that context, returning the answer and its sources.

---

## 🗺️ Roadmap

- [ ] Expand the corpus to official O-RAN Alliance specifications
- [ ] Add retrieval & faithfulness evaluation (Recall@k, MRR, RAGAS)
- [ ] Relevance thresholding + sentence-level citations
- [ ] GPU / hosted inference for embeddings & reranking
- [ ] Authentication, rate limiting, and CI/CD

---

## 📄 License

Released under the MIT License — see `LICENSE`.

## 🙏 Acknowledgements
Built with [LlamaIndex](https://www.llamaindex.ai/), [Qdrant](https://qdrant.tech/), [FastAPI](https://fastapi.tiangolo.com/), [Streamlit](https://streamlit.io/), and Google Gemini.
=======
# 🗼 O-RAN Digital Twin — Knowledge Assistant

> A **Retrieval-Augmented Generation (RAG)** assistant for **O-RAN technical documentation**. Ask questions in natural language and get accurate, **source-grounded** answers drawn only from the indexed documents — no hallucination.

<p>
<img alt="Python" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
<img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white">
<img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
<img alt="Qdrant" src="https://img.shields.io/badge/Qdrant-Vector%20DB-DC244C">
<img alt="LlamaIndex" src="https://img.shields.io/badge/LlamaIndex-Workflows-8A2BE2">
</p>

---

## 📖 Overview

This project indexes O-RAN technical documents into a vector database, then answers user questions through a **two-stage retrieval pipeline** (fast dense retrieval + precise cross-encoder reranking) followed by a large language model that is **constrained to answer only from the retrieved context**. The result is a chat assistant that gives traceable, document-backed answers — and explicitly says when the answer isn't in its sources.

It is fully **containerized** (Docker Compose) and ships with a clean Streamlit chat UI.

---

## ✨ Key Features

- 🔎 **Two-stage retrieval** — dense vector search (recall) + cross-encoder reranking (precision)
- 🧷 **Strict grounding** — answers come only from retrieved sources; refuses out-of-scope questions instead of guessing
- 🧩 **Local embeddings & reranking** — runs on your machine; only generation is hosted
- 🗂️ **Source attribution** — every answer lists the documents it was built from
- ⚡ **Idempotent ingestion** — documents are embedded once; restarts are instant
- 🐳 **One-command deploy** — `docker compose up`

---

## 🏗️ Architecture

```mermaid
flowchart LR
    U["👤 User"] -->|":8501"| GUI["🖥️ Streamlit UI<br/>rag-gui"]
    GUI -->|"POST /api/v1/query :8000"| API["⚙️ FastAPI Core<br/>rag-core-api"]
    API -->|"embed + search"| QD[("🧠 Qdrant<br/>Vector DB")]
    API -->|"generate"| GEM["✨ Gemini 2.5 Flash<br/>(Google API)"]

    classDef ui fill:#00D2FF,stroke:#0077aa,color:#001018,font-weight:bold
    classDef core fill:#FFB454,stroke:#b3701f,color:#1a1a1a,font-weight:bold
    classDef db fill:#DC244C,stroke:#7a1029,color:#fff,font-weight:bold
    classDef ext fill:#8A2BE2,stroke:#4b0f86,color:#fff,font-weight:bold
    class GUI ui
    class API core
    class QD db
    class GEM ext
```

---

## 🔁 RAG Pipeline

```mermaid
flowchart TB
    subgraph ING["📥 Ingestion (once)"]
        direction LR
        P["📄 Documents"] --> S["✂️ Chunk<br/>SentenceSplitter<br/>512 / 64"] --> E1["🔢 Embed<br/>BGE-large"] --> Q1[("Qdrant<br/>upsert")]
    end

    subgraph QRY["💬 Query (per request)"]
        direction LR
        Qn["❓ Question"] --> E2["🔢 Embed query"] --> R["🔎 Retrieve<br/>top-20"] --> RK["🎯 Rerank<br/>cross-encoder → top-5"] --> CTX["🧱 Build context<br/>+ sources"] --> LLM["✨ Gemini<br/>grounded prompt"] --> ANS["✅ Answer + sources"]
    end

    Q1 -.->|"indexed vectors"| R

    classDef ing fill:#0E7C66,stroke:#063f33,color:#fff
    classDef qry fill:#1E5AAE,stroke:#0d2b55,color:#fff
    class P,S,E1,Q1 ing
    class Qn,E2,R,RK,CTX,LLM,ANS qry
```

---

## 🔄 Request Sequence

```mermaid
sequenceDiagram
    actor User
    participant GUI as Streamlit
    participant API as FastAPI
    participant QD as Qdrant
    participant RR as Reranker
    participant GEM as Gemini

    User->>GUI: Ask a question
    GUI->>API: POST /api/v1/query
    API->>API: Embed query (BGE-large)
    API->>QD: Vector search (top-20)
    QD-->>API: Candidate chunks
    API->>RR: Rerank → top-5
    API->>GEM: Context + question (grounded prompt)
    GEM-->>API: Source-grounded answer
    API-->>GUI: { response, sources }
    GUI-->>User: Answer + source list
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **UI** | Streamlit |
| **API** | FastAPI + Uvicorn |
| **Orchestration** | LlamaIndex Workflows (event-driven) |
| **Embeddings** | `BAAI/bge-large-en-v1.5` (1024-d, local) |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` (local) |
| **LLM** | Google Gemini 2.5 Flash |
| **Vector DB** | Qdrant (HNSW, cosine) |
| **Packaging** | Docker + Docker Compose |

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- A **Google AI Studio API key** (for Gemini)

### 1. Configure environment
Create a `.env` file in the project root (see `.env.example`):

```env
QDRANT_HOST=qdrant-db
QDRANT_PORT=6333
COLLECTION_NAME=oran_digital_twin

GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

> ⚠️ **Never commit `.env`.** It's listed in `.gitignore`.

### 2. Add your documents
Place PDFs / Markdown / text files in:
```
data/source_docs/
```

### 3. Launch
```bash
docker compose up -d --build
```

First boot embeds your documents (a few minutes). Watch progress:
```bash
docker compose logs -f rag-core-api
```
Wait for `Application startup complete`.

### 4. Open the app
| Service | URL |
|---|---|
| 🖥️ Chat UI | http://localhost:8501 |
| 📚 API docs | http://localhost:8000/docs |

---

## 🔌 API

**`POST /api/v1/query`**
```json
// request
{ "query": "How is handover managed across Non-RT and Near-RT RIC?" }
```
```json
// response
{
  "query": "...",
  "response": "Source-grounded answer ...",
  "sources": "[1] document.pdf\n[2] document.pdf"
}
```

**`GET /health`** → `{ "status": "healthy" }`

---

## 📁 Project Structure

```
.
├── api/
│   └── main.py              # FastAPI app + endpoints
├── config/
│   └── settings.py          # Central configuration (Pydantic)
├── services/
│   ├── ingestion.py         # Chunk → embed → store (idempotent)
│   ├── pipeline.py          # Retrieve → rerank → generate
│   └── prompt_templates.py
├── gui/
│   └── app.py               # Streamlit chat UI
├── data/source_docs/        # Your documents go here
├── docker/
│   ├── Dockerfile.api
│   └── entrypoint.sh        # Waits for Qdrant, then starts API
├── docker-compose.yml
└── requirements.txt
```

---

## 🧠 How It Works

1. **Ingestion** — documents are split into ~512-token overlapping chunks, embedded with BGE-large, and stored in Qdrant. This runs once; subsequent restarts skip it.
2. **Retrieval** — the query is embedded and matched against stored vectors to recall the top 20 candidates.
3. **Reranking** — a cross-encoder re-scores each (query, chunk) pair jointly and keeps the 5 most relevant.
4. **Generation** — the selected context is injected into a prompt that instructs Gemini to answer **only** from that context, returning the answer and its sources.

---

## 🗺️ Roadmap

- [ ] Expand the corpus to official O-RAN Alliance specifications
- [ ] Add retrieval & faithfulness evaluation (Recall@k, MRR, RAGAS)
- [ ] Relevance thresholding + sentence-level citations
- [ ] GPU / hosted inference for embeddings & reranking
- [ ] Authentication, rate limiting, and CI/CD

---

## 📄 License

Released under the MIT License — see `LICENSE`.

## 🙏 Acknowledgements
Built with [LlamaIndex](https://www.llamaindex.ai/), [Qdrant](https://qdrant.tech/), [FastAPI](https://fastapi.tiangolo.com/), [Streamlit](https://streamlit.io/), and Google Gemini.
>>>>>>> e9c7da2 (Version 5)
