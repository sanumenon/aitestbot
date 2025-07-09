#rag_search.py
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings  # ✅ Best practice as of LangChain v0.2.2+
from langchain.schema import Document

# ✅ Initialize embeddings using HuggingFace model
embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# ✅ Load FAISS index (ensure index exists)
index_path = "rag_index/index.faiss"
if not os.path.exists(index_path):
    raise RuntimeError(f"❌ FAISS index not found at {index_path}. Please ingest a PDF or help URL first.")

db = FAISS.load_local("rag_index", embedding, allow_dangerous_deserialization=True)

# ✅ Function to retrieve top-k similar documents
def retrieve_context(query: str, k: int = 3) -> str:
    results: list[Document] = db.similarity_search(query, k=k)
    return "\n\n".join([r.page_content for r in results])
