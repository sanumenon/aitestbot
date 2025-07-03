import os
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain_community.vectorstores import FAISS

embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

index_path = "rag_index/index.faiss"
if not os.path.exists(index_path):
    raise RuntimeError(f"❌ FAISS index not found at {index_path}. Please ingest a PDF or help URL first.")

db = FAISS.load_local("rag_index", embedding, allow_dangerous_deserialization=True)

def retrieve_context(query: str, k: int = 3) -> str:
    results: list[Document] = db.similarity_search(query, k=k)
    return "\n\n".join([r.page_content for r in results])
