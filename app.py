# app.py
import streamlit as st
from config import get_target_url, DEFAULT_BROWSER
from llm_engine import chat_with_llm, set_llm_mode, initialize_local_model
from memory_manager import MemoryManager
from code_generator import generate_test_code, generate_multiple_tests
from dom_scraper import suggest_validations_smart,suggest_validations
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

# Mapping from intent keywords to relative paths
INTENT_PATH_MAP = {
    "Impact account": "/giving-group/add-donor",
    "campaign": "campaigns/campaign-test-campaign",
    "charity": "/charities/the-thorold-reed-band",
    "group edit": "/groups/demo-group-0fd0a2ff-2d27-4984-ac3f-082d2940bd76/edit",
    "user profile": "user/profile/basic",
    "login": "",
    "dashboard":"/dashboard"
}

def extract_pages_from_prompt(prompt: str) -> list[str]:
    prompt_lower = prompt.lower()
    matched_pages = []

    for keyword, path in INTENT_PATH_MAP.items():
        if keyword.lower() in prompt_lower:
            matched_pages.append((keyword.lower(), path))

    # Sort so "login" always comes first
    matched_pages.sort(key=lambda x: 0 if x[0] == "login" else 1)
    return [p[1] for p in matched_pages]

def sanitize_field_name(name):
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if name[0].isdigit():
        name = f"el_{name}"
    return name

def to_findby_line(el):
    by = el["by"]
    selector = el["selector"]
    field_name = sanitize_field_name(el["name"])
    comment = f'// Type: {el["type"]}, Original name: {el["name"]}'

    warning = ""
    # Warn about numeric-only or UUID-like unstable IDs
    if by == "id" and (selector.isdigit() or re.match(r"^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$", selector)):
        warning = "// ⚠️ Warning: Detected unstable or auto-generated ID\n"

    if by == "id":
        return f'{warning}{comment}\n@FindBy(id = "{selector}")\nprivate WebElement {field_name};'
    elif by == "name":
        return f'{warning}{comment}\n@FindBy(name = "{selector}")\nprivate WebElement {field_name};'
    elif by == "css":
        return f'{warning}{comment}\n@FindBy(css = "{selector}")\nprivate WebElement {field_name};'
    elif by == "xpath":
        return f'{warning}{comment}\n@FindBy(xpath = "{selector}")\nprivate WebElement {field_name};'
    return f'// ❌ Unsupported selector type: {by} for {el["name"]}'

def infer_path_from_prompt(prompt: str):
    prompt_lower = prompt.lower()
    for keyword, path in INTENT_PATH_MAP.items():
        if keyword in prompt_lower:
            return path
    return ""

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
    st.write("Generate and run Selenium Java test cases with LLM & POM support")

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
    env_choice = st.selectbox("Environment", ["stage","production", "qa" ], index=0)
    st.session_state["env_choice"] = env_choice
    custom_url = st.text_input("Override URL (optional)", "")
    st.session_state["custom_url"] = custom_url.strip() if custom_url else None
    browser_choice = st.selectbox("Browser", ["chrome", "firefox"], index=0)
    st.session_state["browser_choice"] = browser_choice
    use_browserstack = st.checkbox("Run on BrowserStack?", False)
    st.session_state["use_browserstack"] = use_browserstack

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
    # else:
        # st.info(f"✅ Model already loaded: {local_model_name}")

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
st.subheader("🗣️ Provide a Functional Test Instruction")
#user_input = st.text_area("💬 Your prompt", key="user_prompt_input")
user_input = st.text_area(label="-", key="user_prompt_input", label_visibility="collapsed")
with st.expander("🔐 Login Credentials (if required)"):
    username = st.text_input("Username", value="", key="username")
    password = st.text_input("Password", type="password", key="password")

send_clicked = st.button("📨 Generate Test cases")

if send_clicked and user_input.strip():
    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # st.info(f"📩 **Send clicked at:** {click_time}")
    def process_user_prompt(prompt):
        st.info("⏳ Processing your prompt with LLM and DOM validation...")
        start = time.time()

        base_url = st.session_state.get("custom_url") or get_target_url(st.session_state.get("env_choice", "stage"))

        # Optional login credentials
        with st.expander("🔐 Login Credentials (optional)", expanded=False):
            username = st.text_input("Username / Email", type="default")
            password = st.text_input("Password", type="password")

        use_cookies = False

        # Infer all relevant pages to visit
        navigation_paths = extract_pages_from_prompt(prompt)
        print(f"🧭 Pages to scrape based on prompt: {navigation_paths}")

        dom_elements = []
        url = base_url  # Default in case no navigation

        for i, rel_path in enumerate(navigation_paths):
            url = f"{base_url.rstrip('/')}/{rel_path.lstrip('/')}" if rel_path else base_url
            print(f"🔗 Scraping page: {url}")

            logged_in_driver = None  # 🔐 Safe init

            try:
                if i == 0 and "login" in rel_path.lower():
                    login_results, logged_in_driver = suggest_validations_smart(
                        url=url,
                        username=username,
                        password=password,
                        use_cookies=use_cookies,
                        return_driver=True
                    )
                    dom_elements += login_results
                    st.success("✅ Logged in and scraped login page.")
                else:
                    dom_elements += suggest_validations(url, driver=logged_in_driver)
                    st.success(f"✅ Scraped: {rel_path or url}")

            except Exception as e:
                st.error(f"❌ Failed scraping {rel_path or url}: {str(e)}")

        # Step 2: Compact DOM Formatting
        from dom_scraper import format_dom_compact
        compact_dom = format_dom_compact(dom_elements)

        messages = []

        # System message with compact DOM instructions
        messages.append({
            "role": "system",
            "content": f"""
            Use *only* the following DOM elements extracted from {url}.
            Each line is in the format:
                field_name | strategy=selector

            Do NOT invent new selectors or field names.

            {compact_dom}

            Generate a Java Page Object class using Selenium + TestNG + Maven.
            Use @FindBy annotations and the PageFactory pattern.
            """.strip()
        })

        # Step 2.5: RAG Help Filtering
        def filter_rag_chunks_by_prompt(rag_text, prompt, min_relevance=0.3):
            from difflib import SequenceMatcher
            return "\n".join(
                line.strip() for line in rag_text.splitlines()
                if SequenceMatcher(None, line.lower(), prompt.lower()).ratio() > min_relevance
            )

        rag_context = retrieve_context(prompt)
        if rag_context:
            filtered_rag = filter_rag_chunks_by_prompt(rag_context, prompt)
            if filtered_rag.strip():
                messages.append({
                    "role": "system",
                    "content": f"📄 Use this filtered help documentation for better understanding:\n\n{filtered_rag}"
                })
                st.info("📚 Filtered help doc context injected.")
            else:
                st.warning("⚠️ No relevant help lines found after filtering.")
        else:
            st.warning("ℹ️ No help documentation retrieved.")

        # Step 3: Combine DOM + Prompt
        if dom_elements:
            dom_context_lines = [to_findby_line(el) for el in dom_elements]
            dom_context = "\n".join(dom_context_lines)
            combined_prompt = f"""
            Here are the DOM elements extracted from {url}. Use *only* these. Do NOT guess or invent any selectors, IDs, or field names.

            {dom_context}

            Now based on this, {prompt}
            """
        else:
            combined_prompt = f"""
            No DOM elements could be extracted from {url}, so you may have to make assumptions.

            {prompt}
            """

        messages.append({"role": "user", "content": combined_prompt})
        st.session_state.chat_history = messages

        print("\n📦 Final messages sent to LLM:")
        for m in messages:
            print(f"\n--- {m['role'].upper()} ---\n{m['content']}")

        # ✅ FIXED: Only once, correctly keyed caching
        cache_key = f"{base_url}::{combined_prompt}"
        cached_code = cache.get_cached(cache_key)

        if cached_code:
            st.success("✅ Retrieved code from intent cache (LLM not called).")
            response = cached_code
            elapsed = "0.0"
        else:
            response, elapsed, token_usage = chat_with_llm(messages, return_usage=True)
            cache.store(cache_key, response)
            messages.append({"role": "assistant", "content": response})
            st.session_state.chat_history = messages
            st.session_state.llm_response_time = f"{elapsed} sec"
            st.success(f"✅ LLM responded in {elapsed} sec")

            with st.expander("🧠 LLM Response", expanded=True):
                st.code(response, language="java")

            # Token diagnostics
            prompt_tokens = token_usage.get("prompt_tokens", "?")
            completion_tokens = token_usage.get("completion_tokens", "?")
            total_tokens = token_usage.get("total_tokens", "?")
            st.info(f"📊 Token usage — Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")

        # ✅ Finalize state
        st.session_state.generated_code_ready = True
        module_hash = hashlib.md5(prompt.encode()).hexdigest()[:6]
        st.session_state.multi_module_specs.append({
            "user_prompt": prompt,
            "url": url,
            "browser": browser_choice,
            "class_name": f"Test{module_hash}",
            "llm_code": response
        })

        return response


    
    chat_response=process_user_prompt(user_input)
    

    # 🧠 Save chat memory to file
    # Only save interaction to TinyDB (no file dump)
    memory.save_interaction(user_input.strip(), chat_response.strip())
    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"📩 **Response received at:** {click_time}")
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

# ✅ Button: Run tests
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

    # --- Extent Report Handling ---
    report_path = os.path.abspath("generated_code/test-output/ExtentReport.html")

    # Wait for report to be written
    max_wait = 15  # seconds
    waited = 0
    while not os.path.exists(report_path) and waited < max_wait:
        time.sleep(1)
        waited += 1

    if os.path.exists(report_path):
        st.session_state["extent_report_ready"] = True
        st.success("✨ Extent report is ready. Scroll down to view options.")

        st.subheader("📄 Extent Report")
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

    else:
        st.warning("⚠️ Extent report not found. Check if test execution was successful.")
        st.session_state["extent_report_ready"] = False


# ✅ Show Extent Report options if ready
# if st.session_state.get("extent_report_ready", False):
#     st.subheader("📄 Extent Report")

#     report_path = os.path.abspath("generated_code/test-output/ExtentReport.html")
#     if os.path.exists(report_path):
#         col1, col2 = st.columns([1, 1])

#         with col1:
#             with open(report_path, "rb") as f:
#                 st.download_button(
#                     "📄 Download Extent Report",
#                     f,
#                     file_name="ExtentReport.html",
#                     mime="text/html"
#                 )

#         with col2:
#             if st.button("🔗 Open Extent Report in Browser"):
#                 webbrowser.open(f"file://{report_path}")
