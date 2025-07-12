# app.py
import streamlit as st
from config import get_target_url, DEFAULT_BROWSER
from llm_engine import chat_with_llm, set_llm_mode, initialize_local_model
from memory_manager import MemoryManager
from code_generator import generate_test_code, generate_multiple_tests
from dom_scraper import suggest_validations, suggest_validations_authenticated
from intent_cache import IntentCache
from executor import execute_tests_live
from tinydb import TinyDB
from doc_ingestor import ingest_doc
from rag_search import retrieve_context
import os
import json
from datetime import datetime
import re
import time
import subprocess
import hashlib
import zipfile
import webbrowser
import time

# ✅ Step 1: Always initialize all session keys FIRST
required_session_keys = {
    "initialized": False,
    "chat_history": [],
    "generated_intent": "",
    "generated_code_ready": False,
    "multi_module_specs": [],
    "llm_response_time": "",
    "local_model_loaded_once": False,
    "last_loaded_model": "",
    "llm_choice": "local",
    "memory_exported": False,
    "local_model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
}

for key, default in required_session_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ✅ Step 2: Now it's safe to use the keys
if not st.session_state.initialized:
    st.set_page_config(page_title="AI Test Bot for Charitable Impact", layout="wide")
    st.title("🤖 AI Test Bot for Charitableimpact")
    st.write("Generate and run Selenium Java test cases with LLM + POM support")

    os.makedirs("cache", exist_ok=True)
    os.makedirs("rag_versions", exist_ok=True)

    st.session_state.initialized = True

# ✅ Step 3: Now continue app logic
memory = MemoryManager()
cache = IntentCache()

def clear_session_memory(full: bool = False):
    """Clear chat history or full memory depending on the flag."""
    base_keys = ["chat_history"]
    full_keys = base_keys + [
        "generated_intent",
        "generated_code_ready",
        "multi_module_specs",
        "llm_response_time",
        "memory_exported"
    ]

    keys_to_clear = full_keys if full else base_keys

    for key in keys_to_clear:
        st.session_state.pop(key, None)


# Sidebar logic for LLM mode, browser, memory management, RAG ingestion, and cache clearing
with st.sidebar:
    st.header("Test Setup")
    env_choice = st.selectbox("Environment", ["production", "qa", "stage"], index=0)
    custom_url = st.text_input("Override URL (optional)", "")
    browser_choice = st.selectbox("Browser", ["chrome", "firefox"], index=0)
    use_browserstack = st.checkbox("Run on BrowserStack?", False)

    llm_choice = st.radio("LLM Mode", ["local", "openai"], index=0)

    if llm_choice == "local":
        st.selectbox("Local Model", [
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "teknium/OpenHermes-2.5-Mistral-7B",
            "mistralai/Mistral-7B-Instruct-v0.2",
            "google/gemma-2b",
        ], key="local_model_name")

    local_model_name = st.session_state.local_model_name

    if (not st.session_state.local_model_loaded_once) or (st.session_state.last_loaded_model != local_model_name):
        with st.spinner(f"🧠 Loading model: {local_model_name}... please wait"):
            success = initialize_local_model(local_model_name)
        if success:
            st.session_state.last_loaded_model = local_model_name
            st.session_state.local_model_loaded_once = True
            st.toast(f"✅ Loaded model: {local_model_name}", icon="🧠")
        else:
            st.error(f"❌ Failed to load model: {local_model_name}")
    else:
        st.info(f"✅ Model already loaded: {local_model_name}")

    if st.session_state.llm_choice != llm_choice:
        st.session_state.llm_choice = llm_choice
        if llm_choice == "openai":
            set_llm_mode(llm_choice)

    st.markdown("---")
    st.subheader("🧹 Memory Controls")
    if st.button("⬇️ Export Memory Before Clearing"):
        if os.path.exists("cache/memory.json"):
            with open("cache/memory.json", "r") as f:
                memory_data = f.read()
            st.download_button("Download Memory Log", data=memory_data, file_name="memory_backup.json", mime="application/json")
            st.session_state.memory_exported = True
        else:
            st.warning("No memory data found to export.")

    if st.button("🧽 Clear Memory After Export"):
        if not st.session_state.get("memory_exported", False):
            st.error("Please export memory first before clearing it.")
        else:
            if os.path.exists("cache/memory.json"):
                db = TinyDB("cache/memory.json")
                db.truncate()

            clear_session_memory(full=True)

            # Restore model state
            st.session_state.last_loaded_model = st.session_state.get("last_loaded_model")
            st.session_state.local_model_loaded_once = st.session_state.get("local_model_loaded_once")

            st.success("✅ Full memory cleared! Chat and test history reset.")


    st.subheader("📄 RAG Setup: Help Docs")
    uploaded_file = st.file_uploader("Upload Help PDF", type="pdf")
    doc_url = st.text_input("Or Enter Help Page URL")

    if st.button("📅 Ingest Help Docs"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        index_path = f"rag_versions/rag_{timestamp}"
        if uploaded_file:
            with open("cache/uploaded_help.pdf", "wb") as f:
                f.write(uploaded_file.getbuffer())
            msg = ingest_doc("cache/uploaded_help.pdf", is_url=False)
            if os.path.exists("rag_index"):
                os.rename("rag_index", index_path)
            st.success(f"{msg} ✅ Snapshot saved at `{index_path}`")
        elif doc_url:
            msg = ingest_doc(doc_url, is_url=True)
            if os.path.exists("rag_index"):
                os.rename("rag_index", index_path)
            st.success(f"{msg} ✅ Snapshot saved at `{index_path}`")
        else:
            st.warning("Please upload a PDF or enter a URL.")

    if st.button("🧹 Clear Intent Cache"):
        last_model = st.session_state.get("last_loaded_model")
        model_loaded_flag = st.session_state.get("local_model_loaded_once")
        msg = cache.clear_cache()
        st.success(msg)
        st.session_state.last_loaded_model = last_model
        st.session_state.local_model_loaded_once = model_loaded_flag

# Final fallback: ensure LLM mode applied if not done earlier
if st.session_state.get("llm_choice") and not st.session_state.get("_llm_set_once"):
    if st.session_state.llm_choice == "openai":
        set_llm_mode("openai")
    elif st.session_state.llm_choice == "local":
        default_model = st.session_state.get("last_loaded_model", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        if not st.session_state.get("local_model_loaded_once"):
            with st.spinner(f"🧠 Auto-loading default model: {default_model}"):
                success = initialize_local_model(default_model)
            if success:
                st.session_state.last_loaded_model = default_model
                st.session_state.local_model_loaded_once = True
                st.toast(f"✅ Loaded model: {default_model}", icon="🧠")
            else:
                st.error(f"❌ Failed to load model: {default_model}")
    st.session_state["_llm_set_once"] = True

# ✅ Prompt input and LLM processing
st.subheader("🗣️ Ask a Test Question or Feature Prompt")
user_input = st.text_area("💬 Your prompt", key="user_prompt_input")
send_clicked = st.button("📨 Send Prompt")

if send_clicked and user_input.strip():
    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"📩 **Send clicked at:** {click_time}")
    def process_user_prompt(prompt):
        st.info("⏳ Processing your prompt with LLM and DOM validation...")
        start = time.time()

        url = custom_url or get_target_url(env_choice)

        try:
            # 🔐 If login details are available, use suggest_validations_authenticated
            # Replace with actual logic if you have login fields
            dom_elements = suggest_validations(url)  # or suggest_validations_authenticated(url, username, password)
        except Exception as e:
            st.warning(f"⚠️ DOM validation failed: {e}")
            dom_elements = []

        # Prepare DOM context to guide the LLM
        dom_context = ""
        if dom_elements:
            dom_context = "\n".join([
                f"{el['name']} → {el['by']}={el['selector']}" for el in dom_elements
            ])
            st.info("✅ DOM elements extracted and injected into the LLM prompt.")

        # Compose LLM prompt with DOM context
        messages = []
        if dom_context:
            messages.append({"role": "system", "content": "Use only the following verified page elements when generating locators or selectors."})
            messages.append({"role": "system", "content": dom_context})

        messages.append({"role": "user", "content": prompt})

        cached_code = cache.get_cached(prompt)
        if cached_code:
            st.success("✅ Retrieved code from intent cache (LLM not called).")
            response = cached_code
            elapsed = "0.0"
        else:
            response, elapsed = chat_with_llm(messages)
            cache.store(prompt, response)

        st.session_state.llm_response_time = f"{elapsed} sec"
        st.success(f"✅ LLM responded in {elapsed} sec")

        with st.expander("🧠 LLM Response", expanded=True):
            st.code(response, language="java")

        st.session_state.generated_code_ready = True

        # ✅ Append to multi_module_specs list for "Generate All"
        module_hash = hashlib.md5(prompt.encode()).hexdigest()[:6]
        st.session_state.multi_module_specs.append({
            "user_prompt": prompt,
            "url": url,
            "browser": browser_choice,
            "class_name": f"Test{module_hash}",
            "llm_code": response
        })


    process_user_prompt(user_input)
    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"📩 **Response received at:** {click_time}")

if send_clicked and user_input.strip():
    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"📩 **Send clicked at:** {click_time}")
    if send_clicked and user_input.strip():
        click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.info(f"📩 **Send clicked at:** {click_time}")

        def process_user_prompt(prompt):
            st.info("⏳ Processing your prompt with LLM...")
            start = time.time()
            # Load chat history or start fresh
            messages = st.session_state.get("chat_history", [])
            # Append new user message
            messages.append({"role": "user", "content": prompt})
            response, elapsed = chat_with_llm(messages)
            # Append assistant's response to history
            messages.append({"role": "assistant", "content": response})
            # Save updated history
            st.session_state.chat_history = messages
            st.session_state.llm_response_time = f"{elapsed} sec"
            st.success(f"✅ LLM responded in {elapsed} sec")
            with st.expander("🧠 LLM Response", expanded=True):
                st.code(response, language="java")

            st.session_state.generated_code_ready = True

        process_user_prompt(user_input)

    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.balloons()
    st.info(f"📩 **Response received at:** {click_time}")
# Show queued modules
if st.session_state.get("multi_module_specs"):
    st.markdown("### 🧾 Queued Modules:")
    for mod in st.session_state.get("multi_module_specs", []):
        st.markdown(f"- `{mod['class_name']}` for {mod['url']}")

# Button: Generate all test modules
generate_clicked = st.sidebar.button("🧪 Generate All Modules", disabled=not st.session_state.get("multi_module_specs", []))
if generate_clicked:
    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"📩 **Generating all test modules clicked at:** {click_time}")
    with st.spinner("🔄 Generating all test modules..."):
        generate_multiple_tests(st.session_state.get("multi_module_specs", []))
    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"📩 **Generating all test modules completed at:** {click_time}")
    st.success("✅ All test classes generated!")
    st.session_state.generated_code_ready = True

    # Offer zip download
    test_zip_path = "cache/generated_tests.zip"
    with zipfile.ZipFile(test_zip_path, 'w') as zipf:
        for root, _, files in os.walk("generated_code"):
            for file in files:
                full_path = os.path.join(root, file)
                zipf.write(full_path, os.path.relpath(full_path, "generated_code"))
    with open(test_zip_path, "rb") as f:
        st.sidebar.download_button("⬇️ Download Generated Tests", f, file_name="generated_tests.zip")

# ✅ Final Test Execution Log and Report section
# (Replaces existing final test execution log and extent report handling)

# Button: Run tests
run_clicked = st.sidebar.button("✅ Run Test Now", disabled=not st.session_state.get("generated_code_ready", False))
if run_clicked:
    st.markdown("**📆 Packaging Maven project and starting WebDriver session...**")
    log_box = st.empty()

    def stream_logs():
        try:
            process = subprocess.Popen(
                ["mvn", "clean", "test"],
                cwd="generated_code",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            full_log = ""
            for line in iter(process.stdout.readline, ''):
                full_log += line
                log_box.code(full_log, language="bash")
            process.wait()
            return full_log
        except Exception as e:
            return f"❌ Error during execution: {e}"

    with st.spinner("🚀 Running your test..."):
        final_logs = stream_logs()

    st.success("✅ Test execution completed!")
    st.subheader("🚀 Final Test Execution Log")
    st.code(final_logs, language="bash")
    st.session_state.test_execution_complete = True

    # --- Updated Extent Report Handling ---
    report_path = os.path.abspath("generated_code/test-output/ExtentReport.html")

    # Wait for report to be written
    max_wait = 15  # seconds
    waited = 0
    while not os.path.exists(report_path) and waited < max_wait:
        time.sleep(1)
        waited += 1

    if os.path.exists(report_path):
        col1, col2 = st.columns([1, 1])

        with open(report_path, "rb") as f:
            with col1:
                st.download_button(
                    "📄 Download Extent Report",
                    f,
                    file_name="ExtentReport.html",
                    mime="text/html"
                )

        with col2:
            if st.button("🔗 Open Extent Report in Browser"):
                webbrowser.open(f"file://{report_path}")

        st.success("✨ Extent report is ready. You can open it in your browser or download it.")
    else:
        st.warning("⚠️ Extent report not found. Check if test execution was successful.")
