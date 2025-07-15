AI TestBot for Test case Generation
Repository: https://github.com/sanumenon/aitestbot

AI TestBot is a Streamlit-based application that enables users to generate, execute, and download Java test automation code (using Selenium and TestNG). It supports natural language prompts, integrates with LLMs (local or OpenAI), handles optional Retrieval-Augmented Generation (RAG) via documentation ingestion, and provides interactive test execution and reporting.

Folder Structure
graphql
Copy
Edit
aitestbot/
├── app.py               # Streamlit UI and orchestration logic
├── llm_engine.py        # Handles LLM setup and prompt communication
├── code_generator.py    # Converts prompts to Java automation code
├── dom_scraper.py       # Helps identify DOM elements for test code
├── executor.py          # Triggers Maven test execution and streams logs
├── intent_cache.py      # Saves prompt→code mappings to reduce regeneration
├── memory_manager.py    # Maintains multi-turn conversation context
├── doc_ingestor.py      # Ingests PDFs or URLs and creates FAISS index (for RAG)
├── rag_search.py        # Retrieves context from ingested documents
├── generated_code/      # Output directory for generated test code projects
└── cache/               # Stores session data and RAG indices
Installation
Prerequisites
Python 3.10 or higher

Git

(Optional) OpenAI API key for online LLM usage

(Optional) ChromeDriver/GeckoDriver for local Selenium

(Optional) Maven 3.x for Java project builds

Setup
bash
Copy
Edit
git clone https://github.com/sanumenon/aitestbot.git
cd aitestbot
pip install -r requirements.txt
Dependencies include streamlit, transformers, openai, faiss-cpu, langchain-community, beautifulsoup4, tinydb, among others.

Usage
Launch Application
bash
Copy
Edit
streamlit run app.py
Sidebar Controls:
Environment: Select from production, qa, or stage

Target URL: e.g., https://qa.charitableimpact.com

LLM Mode: Choose between local model (e.g., TinyLlama) or OpenAI

Ingest Documentation: Upload PDF or enter URL for RAG context

Memory / Cache Options: Manage cached prompts and history

Primary Workflows
Prompt-Only Testing

Enter natural language test scenario

Generate Java + Selenium + TestNG code

Execute immediately and download ExtentReport output

RAG-Assisted Testing

Ingest relevant docs or URLs

Generate context-enriched test code

Execute and export results

Intent Caching

Reuse previously generated code for repeat prompts via IntentCache

Module Overview
llm_engine.py: Facilitates communication with chosen LLM (local or OpenAI)

code_generator.py: Transforms prompt documents into Java-based test files

doc_ingestor.py: CLI support for PDF/URL ingestion and FAISS index creation

executor.py: Runs generated projects via Maven, streams console and builds

rag_search.py: Retrieves document context to enrich code generation

intent_cache.py: Improves performance by storing and reusing generated test code

CI/CD Support
A Dockerfile and GitHub Actions configuration allow headless build, test execution, and report generation.

Integrates generated code tests into CI pipelines to maintain continuous quality validation.
