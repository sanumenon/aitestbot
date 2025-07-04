Here’s a polished, comprehensive **README.md** for your **AI Test Bot** project, tailored to developers with basic programming knowledge. It clearly explains the project purpose, folder structure, installation, usage flows (including optional RAG ingestion), and common scenarios.

---

# 🤖 AI Test Bot for Charitableimpact.com

A Streamlit-based tool that enables non-technical users to **generate**, **run**, and **download** Java test automation code (Selenium + TestNG + Maven) for `charitableimpact.com`. It integrates LLMs (Local or OpenAI), DOM scraping, intent caching, and optional RAG-based help doc ingestion.

---

## 📁 Folder Structure

```
aitestbot/
├── app.py                     # Main Streamlit UI and orchestrator
├── llm_engine.py             # LLM setup & chat logic (local/openai)
├── code_generator.py        # Java test code generation logic
├── dom_scraper.py           # HTML element identification utilities
├── executor.py              # Executes Maven and streams logs
├── intent_cache.py          # Caches user prompts & generated code
├── memory_manager.py        # Tracks conversation context
├── doc_ingestor.py          # (Enhanced) PDF/URL ingestion → FAISS index
├── rag_search.py            # RAG memory retrieval
├── generated_code/          # Maven project output
└── cache/                   # Session & RAG index storage
```

---

## 🛠️ Setup & Installation

### Prerequisites:

* Python 3.10+
* Git
* (Optional) OpenAI API key

### Install dependencies:

```bash
git clone https://github.com/sanumenon/aitestbot.git
cd aitestbot
pip install -r requirements.txt
```

**Requirements include:**
`streamlit`, `transformers`, `openai`, `faiss-cpu`, `langchain-community`, `beautifulsoup4`, `tinydb`, etc.

### Optional:

* Chrome or Geckodriver for local Selenium
* Maven 3.x

---

## 🚀 Run the App

```bash
streamlit run app.py
```

Key sidebar controls:

* **Environment**: `production`, `qa`, or `stage`
* **Custom URL**: e.g. `https://qa.my.charitableimpact.com`
* **LLM Mode**: Use local models (e.g., TinyLlama) or OpenAI
* **Ingest Help Docs**: Use a PDF or URL to index help content (RAG)
* **Memory / Intent Cache**: For cleaning or exporting chat logs

---

## ⚙️ Usage Scenarios

### 1. **Generate Test Case (No RAG)**

* Enter test prompt:
  `"Login with admin@example.com/pass123 and verify dashboard widgets."`
* Bot generates `Java + Selenium + TestNG` code
* Code saved under `generated_code/src/...`
* Run tests via sidebar → click **Run Test Now**
* Download Extent Report or manually open

### 2. **Generate Test Case (With RAG)**

* Upload PDF or enter URL in sidebar → click **Ingest Help Docs**
* Bot uses RAG content to inform test generation
* Execute test steps similar to (1)

### 3. **Cache Reuse**

* Same prompt → uses `IntentCache`, reuses previously generated code instantly

---

## 📝 README Walkthrough

### 1. **`llm_engine.py`**

* Loads local (TinyLlama/Mistral) or OpenAI
* `chat_with_llm()` adds a system prompt to restrict LLM to:

  * `charitableimpact.com`
  * Java + Selenium + TestNG + Maven only
* Returns `(response, elapsed_time)`

### 2. **`intent_cache.py`**

* Uses `TinyDB` to store prompt→hash→code mapping
* Ensures prompt reuse speeds up repeated generations

### 3. **`doc_ingestor.py`**

* CLI entry: `python doc_ingestor.py <path_or_URL> <true/false>`
* PDF ingestion or multi-page web scraping (BeautifulSoup + WebBaseLoader)
* Splits docs, builds FAISS index in `../cache/rag_index`
* Used in RAG-based generation to provide context

### 4. **`app.py` Flow**

* Builds chat history, caches user queries
* Calls `chat_with_llm()` to generate test code
* Queues modules, optionally batches with sidebar button
* Runs tests, shows logs, packaging, Extent Report download

---

## ✅ Optional Profiles

| Feature               | Command / UI action                                             |
| --------------------- | --------------------------------------------------------------- |
| Run with OpenAI       | Set LLM Mode = **OpenAI** (API key needed)                      |
| Use local LLM         | Set LLM Mode = **Local**, pick model (TinyLlama, Mistral, etc.) |
| Ingest PDF help docs  | Upload PDF → press **📥 Ingest Help Docs**                      |
| Ingest URL help docs  | Enter doc URL → press **📥 Ingest Help Docs**                   |
| Generate test modules | Use chat + press **Generate All Modules** on sidebar            |
| Run tests             | Press **Run Test Now** → view logs, download report             |

---

## 🛡️ Troubleshooting & Tips

* **Browser not opening**: Download Extent Report manually and open locally
* **Local model issues**: Ensure sufficient RAM or GPU and use `device_map="auto"`
* **Maven build fails**: Inspect logs streamed in UI, ensure `pom.xml` is correct
* **RAG indexing**: If `rag_index` appears empty, check internet connectivity and PDF validity

---

## ⏩ Next Steps

* Extend support for other test frameworks (e.g. JUnit)
* Add CI/CD integration to save snapshots of generated code
* Automatically embed Extent Report in Streamlit via iframe
* Support other vector stores (e.g. Chroma, Weaviate)

---

## 🧑‍💻 Contribution

Feel free to:

* Raise issues
* Suggest enhancements
* Submit pull requests

---

## 🧾 License

MIT License — refer to `LICENSE` file.

---

Let me know if you'd like a **visual diagram** or **CLI-only usage guide** as a separate section.

