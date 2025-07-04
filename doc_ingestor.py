# doc_ingestor.py (Enhanced with multi-page URL scraping support)

import os
import requests
from bs4 import BeautifulSoup
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

def get_all_help_links(base_url: str) -> list:
    """
    Crawl all internal help page links from the given base URL.
    """
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag['href']
            if href.startswith("/"):
                links.add(base_url.rstrip("/") + href)
            elif href.startswith(base_url):
                links.add(href)
        return list(links)
    except Exception as e:
        print(f"❌ Failed to crawl: {e}")
        return [base_url]  # fallback to base page only

def ingest_doc(source_path_or_url="cache/uploaded_help.pdf", is_url=False):
    """
    Ingests either a PDF file or all help pages from a URL, and stores FAISS index locally.
    """
    if is_url:
        print(f"🌐 Crawling and loading from: {source_path_or_url}")
        all_links = get_all_help_links(source_path_or_url)
        print(f"🔗 Found {len(all_links)} links.")
        loader = WebBaseLoader(all_links)
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
    import sys
    source = sys.argv[1] if len(sys.argv) > 1 else "cache/uploaded_help.pdf"
    is_url = sys.argv[2].lower() == "true" if len(sys.argv) > 2 else False
    print(ingest_doc(source, is_url))
# Example usage:
# python doc_ingestor.py "https://example.com/help" true
# python doc_ingestor.py "cache/uploaded_help.pdf" false
# This script can be run directly to ingest documents or URLs and create a FAISS index.
# It supports both PDF files and crawling multiple help pages from a URL.
# The index is saved locally for later retrieval in RAG workflows.
# Make sure to install required packages: requests, beautifulsoup4, langchain_community
# You can install them via pip:
# pip install requests beautifulsoup4 langchain-community
# Ensure you have the necessary environment set up for LangChain and FAISS.
# This script is designed to be run in a Python environment with access to the internet for URL crawling.
# It can be integrated into larger applications or used as a standalone tool for document ingestion.        