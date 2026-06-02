import json
import asyncio
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder

from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.core.schema import NodeWithScore
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.llms.gemini import Gemini
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step, Event

from config.settings import settings


ORAN_LAYER_KEYWORDS = {
    "Near-RT-RIC": ["near-rt ric", "xapp", "e2 interface", "e2ap", "e2sm", "kpm"],
    "Non-RT-RIC": ["non-rt ric", "rapp", "a1 policy", "smo"],
    "O-CU": ["o-cu", "cu-cp", "cu-up", "f1 interface"],
    "O-DU": ["o-du", "du", "mac", "rlc"],
    "O-RU": ["o-ru", "ru", "fronthaul"],
    "digital_twin": ["digital twin", "rl agent", "synchronization"],
    "kubernetes": ["kubernetes", "helm", "pod", "deployment"]
}


class QueryAnalysisEvent(Event):
    refined_query: str
    oran_layer: str


class RetrievalEvent(Event):
    nodes: List[NodeWithScore]


class TelecomAgentWorkflow(Workflow):

    def __init__(self, index: VectorStoreIndex, qdrant_client: QdrantClient, **kwargs):
        super().__init__(**kwargs)

        self.index = index
        self.client = qdrant_client

        self.local_llm = Ollama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            request_timeout=60.0
        )

        self.gemini_llm = Gemini(
            model=settings.GEMINI_MODEL,
            api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )

        # ✅ Correct reranker
        self.reranker = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

    # ---------------- QUERY ANALYSIS ----------------
    @step
    async def analyze_query(self, ev: StartEvent) -> QueryAnalysisEvent:

        user_query = ev.query

        prompt = f"""
Analyze this O-RAN telecom query:
"{user_query}"

Return STRICT JSON ONLY:
{{
  "refined_query": "clean technical query",
  "oran_layer": "Near-RT-RIC | Non-RT-RIC | O-CU | O-DU | O-RU | digital_twin | kubernetes | None"
}}
"""

        response = await self.local_llm.acomplete(prompt)

        try:
            data = json.loads(response.text.strip())
            refined_query = data.get("refined_query", user_query)
            oran_layer = data.get("oran_layer", "None")
        except Exception:
            refined_query = user_query
            oran_layer = "None"

        return QueryAnalysisEvent(
            refined_query=refined_query,
            oran_layer=oran_layer
        )

    # ---------------- RETRIEVAL + RERANK ----------------
    @step
    async def retrieve_context(self, ev: QueryAnalysisEvent) -> RetrievalEvent:

        retriever = self.index.as_retriever(similarity_top_k=20)
        nodes = retriever.retrieve(ev.refined_query)

        if not nodes:
            return RetrievalEvent(nodes=[])

        # Prepare reranker input
        pairs = [
            (ev.refined_query, node.node.get_content())
            for node in nodes
        ]

        scores = self.reranker.predict(pairs)

        scored_nodes = list(zip(nodes, scores))
        scored_nodes.sort(key=lambda x: x[1], reverse=True)

        filtered_nodes = [node for node, score in scored_nodes[:5]]

        return RetrievalEvent(nodes=filtered_nodes)

    # ---------------- GENERATION ----------------
    @step
    async def generate_answer(self, ev: RetrievalEvent) -> StopEvent:

        context_parts = []
        source_parts = []

        for i, node_with_score in enumerate(ev.nodes, 1):

            meta = node_with_score.node.metadata or {}
            source = meta.get("file_name", "unknown_source")
            layers = ", ".join(meta.get("oran_layers", ["general"]))

            context_parts.append(
                f"[{i}] SOURCE: {source} | Layers: {layers}\n"
                f"{node_with_score.node.get_content()}"
            )

            source_parts.append(f"[{i}] {source}")

        context_str = "\n\n---\n\n".join(context_parts)
        sources_str = "\n".join(source_parts)

        full_prompt = f"""
You are an expert O-RAN & Digital Twin engineer.

Use ONLY the context below.

Context:
{context_str}

Sources:
{sources_str}

Question:
{self.get_current_query_string()}

Answer clearly and technically:
"""

        response = await self.gemini_llm.acomplete(full_prompt)

        return StopEvent(result={
            "response": response.text,
            "sources": sources_str
        })

    # ---------------- UTILITY ----------------
    def get_current_query_string(self) -> str:
        return getattr(self, "_current_query", "O-RAN System Query")


# ---------------- PIPELINE WRAPPER ----------------
class TelecomRAGPipeline:

    def __init__(self):

        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )

        LlamaSettings.embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL
        )

        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=settings.COLLECTION_NAME
        )

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store
        )

    def query(self, query_str: str) -> Dict[str, Any]:

        workflow = TelecomAgentWorkflow(
            index=self.index,
            qdrant_client=self.client
        )

        workflow._current_query = query_str

        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            workflow.run(query=query_str)
        )

        return {
            "query": query_str,
            "response": result["response"],
            "sources": result["sources"]
        }