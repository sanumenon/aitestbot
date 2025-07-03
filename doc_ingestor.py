# doc_ingestor.py (updated from ingest_docs.py)

import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


def ingest_doc(source_path_or_url="cache/uploaded_help.pdf", is_url=False):
    """
    Ingests either a PDF file or a help documentation URL and stores FAISS index locally.
    """
    if is_url:
        print(f"🌐 Loading web content from: {source_path_or_url}")
        loader = WebBaseLoader(source_path_or_url)
    else:
        if not os.path.exists(source_path_or_url):
            print(f"❌ File not found: {source_path_or_url}")
            return "❌ File not found."
        print(f"📄 Loading PDF: {source_path_or_url}")
        loader = PyPDFLoader(source_path_or_url)

    try:
        documents = loader.load()
    except Exception as e:
        return f"❌ Error loading documents: {e}"

    print(f"✂️ Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(documents)

    print(f"🔎 Embedding and indexing...")
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(chunks, embedding)

    index_path = "rag_index"
    print(f"💾 Saving index to: {index_path}")
    vectorstore.save_local(index_path)

    return f"✅ Ingested {'URL' if is_url else 'PDF'} and saved index."

# Optional CLI usage
if __name__ == "__main__":
    # Default: PDF mode
   # print(ingest_doc("cache/uploaded_help.pdf", is_url=False))
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else "cache/uploaded_help.pdf"
    is_url = sys.argv[2].lower() == "true" if len(sys.argv) > 2 else False
    print(ingest_doc(source, is_url))

#use the command to have the above executed: python doc_ingestor.py "https://help.charitableimpact.com/" True