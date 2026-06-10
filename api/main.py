import traceback
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

from google.genai.errors import ServerError

from services.pipeline import TelecomRAGPipeline
from services.ingestion import TelecomIngestionEngine

app = FastAPI(
    title="O-RAN Digital Twin Knowledge Core API",
    description="Production-grade local RAG pipeline engine optimized for context injection over O-RAN specs.",
    version="1.0.0"
)

rag_pipeline = None


class QueryRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None


@app.on_event("startup")
async def startup_event():
    global rag_pipeline
    try:
        ingest_engine = TelecomIngestionEngine()
        ingest_engine.run_ingestion(data_dir="/app/data/source_docs")
    except Exception as e:
        print(f"[-] Automated boot ingestion pass bypassed or failed: {str(e)}")

    rag_pipeline = TelecomRAGPipeline()


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "O-RAN RAG Core"}


@app.post("/api/v1/query")
async def process_rag_query(payload: QueryRequest):
    global rag_pipeline

    if not rag_pipeline:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG pipeline not initialized.",
        )

    try:
        execution_result = await rag_pipeline.query(payload.query)
        return execution_result

    except ServerError:
        # Gemini servers are temporarily overloaded / unavailable.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini servers are currently overloaded. Please try again in a few seconds.",
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline Execution Abort: {str(e)}",
        )