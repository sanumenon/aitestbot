AI TestBot for Test case Generation
Repository: https://github.com/sanumenon/aitestbot

AI TestBot is a Streamlit-based application that enables users to generate, execute, and download Java test automation code (using Selenium and TestNG). It supports natural language prompts, integrates with LLMs (local or OpenAI), handles optional Retrieval-Augmented Generation (RAG) via documentation ingestion, and provides interactive test execution and reporting.

Folder Structure


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

1. Python 3.10 or higher
2. Git
3. (Optional) OpenAI API key for online LLM usage
4. (Optional) ChromeDriver/GeckoDriver for local Selenium
5. (Optional) Maven 3.x for Java project builds

Setup

1. git clone https://github.com/sanumenon/aitestbot.git
2. cd aitestbot
3. pip install -r requirements.txt
4. Dependencies include streamlit, transformers, openai, faiss-cpu, langchain-community, beautifulsoup4, tinydb, among others.

Usage

Launch Application from terminal : streamlit run app.py

Sidebar Controls:

1. Environment: Select from production, qa, or stage
2. Target URL: e.g., https://my.charitableimpact.com
3. LLM Mode: Choose between local model (e.g., TinyLlama) or OpenAI
4. Ingest Documentation: Upload PDF or enter URL for RAG context
5. Memory / Cache Options: Manage cached prompts and history

Primary Workflows
1. Prompt-Only Testing
		Enter natural language test scenario
		Generate Java + Selenium + TestNG code
		Execute immediately and download ExtentReport output
2. RAG-Assisted Testing
		Ingest relevant docs or URLs
		Generate context-enriched test code
		Execute and export results
3. Intent Caching
		Reuse previously generated code for repeat prompts via IntentCache

Module Overview
	1. llm_engine.py: Facilitates communication with chosen LLM (local or OpenAI)
	2. code_generator.py: Transforms prompt documents into Java-based test files
	3.	doc_ingestor.py: CLI support for PDF/URL ingestion and FAISS index creation
	4.	executor.py: Runs generated projects via Maven, streams console and builds
	5. rag_search.py: Retrieves document context to enrich code generation
	6. intent_cache.py: Improves performance by storing and reusing generated test code

CI/CD Support
	1. A Dockerfile and GitHub Actions configuration allow headless build, test execution, and report generation.
	2. Integrates generated code tests into CI pipelines to maintain continuous quality validation.
