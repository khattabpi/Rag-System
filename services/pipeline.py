from typing import List, Dict, Any

from qdrant_client import QdrantClient, AsyncQdrantClient
from sentence_transformers import CrossEncoder

from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.core.schema import NodeWithScore
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.workflow import Workflow, StartEvent, StopEvent, step, Event

from config.settings import settings


class RetrievalEvent(Event):
    query: str
    nodes: List[NodeWithScore]


class TelecomAgentWorkflow(Workflow):

    def __init__(
        self,
        index: VectorStoreIndex,
        reranker: CrossEncoder,
        gemini_llm: GoogleGenAI,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.index = index
        self.reranker = reranker
        self.gemini_llm = gemini_llm

    @step
    async def retrieve_context(self, ev: StartEvent) -> RetrievalEvent:
        query = ev.query

        retriever = self.index.as_retriever(similarity_top_k=20)
        nodes = await retriever.aretrieve(query)

        if not nodes:
            return RetrievalEvent(query=query, nodes=[])

        # Cross-encoder re-ranking: score each (query, chunk) pair
        pairs = [(query, node.node.get_content()) for node in nodes]
        scores = self.reranker.predict(pairs)

        scored_nodes = list(zip(nodes, scores))
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        filtered_nodes = [node for node, _ in scored_nodes[:5]]

        return RetrievalEvent(query=query, nodes=filtered_nodes)

    @step
    async def generate_answer(self, ev: RetrievalEvent) -> StopEvent:

        if not ev.nodes:
            return StopEvent(result={
                "response": "Context Insufficient for Telecom Spec Verification — no relevant documents were retrieved.",
                "sources": "",
            })

        context_parts = []
        source_parts = []

        for i, node_with_score in enumerate(ev.nodes, 1):
            meta = node_with_score.node.metadata or {}
            source = meta.get("file_name", "unknown_source")
            layer = meta.get("oran_layer", "general")

            context_parts.append(
                f"[{i}] SOURCE: {source} | Layer: {layer}\n"
                f"{node_with_score.node.get_content()}"
            )
            source_parts.append(f"[{i}] {source}")

        context_str = "\n\n---\n\n".join(context_parts)
        sources_str = "\n".join(source_parts)

        full_prompt = f"""
You are an expert O-RAN & Digital Twin engineer.

Use ONLY the context below to answer the question. If the answer cannot be
found in the context, say so explicitly instead of guessing.

Context:
{context_str}

Question:
{ev.query}

Answer clearly and technically:
"""

        response = await self.gemini_llm.acomplete(full_prompt)

        return StopEvent(result={
            "response": response.text,
            "sources": sources_str,
        })


class TelecomRAGPipeline:

    def __init__(self):
        self.client = QdrantClient(
            url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
            timeout=60.0,
        )

        # Async client — required for retriever.aretrieve()
        self.aclient = AsyncQdrantClient(
            url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
            timeout=60.0,
        )

        LlamaSettings.embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL
        )

        self.vector_store = QdrantVectorStore(
            client=self.client,
            aclient=self.aclient,
            collection_name=settings.COLLECTION_NAME,
        )

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store
        )

        # Loaded ONCE at startup, reused across all queries
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        self.gemini_llm = GoogleGenAI(
            model=settings.GEMINI_MODEL,
            api_key=settings.GOOGLE_API_KEY,
        )

        self.workflow = TelecomAgentWorkflow(
            index=self.index,
            reranker=self.reranker,
            gemini_llm=self.gemini_llm,
            timeout=120,
        )

    async def query(self, query_str: str) -> Dict[str, Any]:
        result = await self.workflow.run(query=query_str)
        return {
            "query": query_str,
            "response": result["response"],
            "sources": result["sources"],
        }