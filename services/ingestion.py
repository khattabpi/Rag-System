import os
from pathlib import Path

from qdrant_client import QdrantClient
from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    Settings as LlamaSettings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from config.settings import settings


class TelecomIngestionEngine:
    def __init__(self):
        self.client = QdrantClient(
            url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
            timeout=60.0,
        )
        self.embed_model = HuggingFaceEmbedding(model_name=settings.EMBEDDING_MODEL)

    def extract_metadata(self, file_path: str) -> dict:
        path = Path(file_path).name.lower()
        meta = {"file_name": path, "oran_layer": "Cross-Layer", "interface": "None"}

        if "e2" in path or "xapp" in path:
            meta["oran_layer"] = "Near-RT-RIC"
            meta["interface"] = "E2"
        elif "a1" in path or "non-rt" in path or "policy" in path:
            meta["oran_layer"] = "Non-RT-RIC"
            meta["interface"] = "A1"
        elif "o1" in path:
            meta["interface"] = "O1"

        if path.endswith(".pdf"):
            meta["document_type"] = "research_paper"
        elif path.endswith(".md"):
            meta["document_type"] = "markdown_documentation"
        else:
            meta["document_type"] = "architecture_document"

        return meta

    def _collection_has_data(self) -> bool:
        """True لو الـ collection موجودة وفيها points بالفعل."""
        try:
            if not self.client.collection_exists(settings.COLLECTION_NAME):
                return False
            return self.client.count(settings.COLLECTION_NAME).count > 0
        except Exception:
            return False

    def run_ingestion(self, data_dir: str):
        if not os.path.exists(data_dir) or not os.listdir(data_dir):
            print(f"[!] Target directory '{data_dir}' is empty. Skipping index initialization.")
            return

        # متعملش ingestion تاني لو الـ collection فيها داتا.
        # عشان تجبر إعادة ingestion (مثلاً بعد تغيير الـ chunking أو إضافة
        # ملفات جديدة)، امسح الـ Qdrant volume الأول: docker compose down -v
        if self._collection_has_data():
            print("[=] Collection already populated. Skipping ingestion.")
            return

        print(f"[*] Ingesting technical documents from {data_dir}...")
        reader = SimpleDirectoryReader(
            input_dir=data_dir,
            file_metadata=self.extract_metadata,
            required_exts=[".pdf", ".md", ".txt"],
        )
        documents = reader.load_data()

        # تقطيع مسطّح: كل chunk بيشيل فقرة متماسكة (~512 token)
        node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)
        nodes = node_parser.get_nodes_from_documents(documents)

        vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=settings.COLLECTION_NAME,
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        LlamaSettings.embed_model = self.embed_model

        VectorStoreIndex(
            nodes,
            storage_context=storage_context,
            show_progress=True,
        )
        print("[+] Vector space and payload indexing completed successfully.")