from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.pipeline import TelecomRAGPipeline
from services.ingestion import TelecomIngestionEngine

app = FastAPI(
    title="O-RAN Digital Twin Knowledge Core API",
    description="Production-grade local RAG pipeline engine optimized for context injection over O-RAN specs.",
    version="1.0.0"
)

# Shared memory runtime pipelines
rag_pipeline = None

class QueryRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None

@app.on_event("startup")
def startup_event():
    global rag_pipeline
    # Run targeted local sync pass immediately inside shared folder mappings
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
def process_rag_query(payload: QueryRequest):
    global rag_pipeline
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG Execution pipeline initialization state failure.")
    try:
        execution_result = rag_pipeline.query(payload.query, filter_dict=payload.filters)
        return execution_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline Execution Abort: {str(e)}")