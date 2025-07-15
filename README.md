# Project Overview

This project is a Python-based test automation framework that integrates with Java-based test execution. It provides a seamless workflow for generating test automation code, executing tests, and reviewing reports. The project uses `Streamlit` for the user interface, `Jinja2` for templating, and `FAISS` for retrieval-augmented generation (RAG) workflows. Below is a detailed description of how the files interact with each other and their individual roles.

---

## File Interactions and Workflow

1. **User Interaction**:
   - The user interacts with the application through the `Streamlit` interface provided by app.py.
   - Inputs such as test requirements, DOM elements, or prompts are processed by various backend modules.

2. **Code Generation**:
   - code_generator.py uses user inputs to generate Java test automation code.
   - It relies on templates stored in the templates directory to create test classes, page objects, and Maven configuration files.

3. **Test Execution**:
   - Once the code is generated, executor.py executes the tests using Maven commands.
   - Logs from the execution are streamed back to the user interface in real-time.

4. **Report Generation**:
   - After test execution, Extent Reports are generated and stored in the `generated_code/test-output/` directory.
   - The user can download these reports directly from the interface.

5. **Context Management**:
   - memory_manager.py tracks the conversation context to maintain continuity in user interactions.
   - intent_cache.py caches user prompts and generated code for reuse, improving efficiency.

6. **RAG Workflow**:
   - doc_ingestor.py ingests documents (PDFs or URLs) to build FAISS indexes stored in the rag_index directory.
   - rag_search.py retrieves relevant context from these indexes to assist in generating accurate test code.

7. **DOM Scraping**:
   - dom_scraper.py extracts metadata from DOM elements provided by the user.
   - This metadata is used to suggest validations or generate page object methods.

8. **LLM Integration**:
   - llm_engine.py manages interactions with local or OpenAI LLMs to generate test code or provide suggestions.

---

## File Descriptions

### Core Application Files

- **`app.py`**:
  - The main entry point for the application.
  - Provides a `Streamlit`-based user interface for test generation, execution, and report download.

- **`config.py`**:
  - Contains configuration settings and utility functions used across the application.

- **`executor.py`**:
  - Executes Maven commands to compile and run the generated Java test code.
  - Streams logs from the execution process to the user interface.

- **`memory_manager.py`**:
  - Tracks the conversation context to maintain continuity in user interactions.
  - Stores session data in memory.json.

- **`intent_cache.py`**:
  - Caches user prompts and generated code in intent_cache.json for reuse.

---

### Code Generation

- **`code_generator.py`**:
  - Generates Java test automation code using user inputs and Jinja2 templates.
  - Outputs the generated code to the generated_code directory.

- **templates**:
  - Contains Jinja2 templates for generating Java code:
    - `test_template.java.j2`: Template for test classes.
    - `page_template.java.j2`: Template for page object classes.
    - `pom.xml.j2`: Template for Maven POM files.

---

### RAG Workflow

- **`doc_ingestor.py`**:
  - Ingests documents (PDFs or URLs) to build FAISS indexes.
  - Stores indexes in the rag_index directory.

- **`rag_search.py`**:
  - Retrieves relevant context from FAISS indexes to assist in generating accurate test code.

- **rag_index**:
  - Stores FAISS indexes for retrieval-augmented generation workflows.

- **rag_versions**:
  - Stores snapshots of FAISS indexes for versioning.

---

### DOM Scraping

- **`dom_scraper.py`**:
  - Extracts metadata from DOM elements provided by the user.
  - Suggests validations or generates page object methods based on the extracted metadata.

---

### LLM Integration

- **`llm_engine.py`**:
  - Manages interactions with local or OpenAI LLMs.
  - Generates test code or provides suggestions based on user inputs.

---

### Generated Code and Reports

- **generated_code**:
  - Contains the output of the code generation process:
    - `src/`: Source code for generated tests.
    - `pom.xml`: Maven configuration for the generated project.
    - `test-output/`: Extent Reports and screenshots.

- **cache**:
  - Stores temporary files and session data:
    - `generated_tests/`: Contains Maven target directories and test artifacts.
    - `intent_cache.json`: Caches user intents.
    - `memory.json`: Stores session memory.

---

### Other Files

- **`requirements.txt`**:
  - Lists the Python dependencies required for the project.

- **`.env`**:
  - Stores environment variables for configuration.

- **`README.md`**:
  - Documentation for the project.

---

## Summary

This project is designed to streamline the process of generating, executing, and reviewing test automation code. Each file plays a specific role in the workflow, from user interaction to report generation. The modular structure ensures that components can be reused or extended as needed.