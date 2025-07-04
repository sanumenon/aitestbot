# app.py
import streamlit as st
from config import get_target_url, DEFAULT_BROWSER
from llm_engine import chat_with_llm, set_llm_mode,initialize_local_model
from memory_manager import MemoryManager
from code_generator import generate_test_code, generate_multiple_tests
from dom_scraper import suggest_validations, suggest_validations_authenticated
from intent_cache import IntentCache
from executor import execute_tests_live
from tinydb import TinyDB
from doc_ingestor import ingest_doc
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

# Set Streamlit UI layout and title
st.set_page_config(page_title="AI Test Bot for Charitable Impact", layout="wide")
st.title("🤖 AI Test Bot for Charitableimpact")
st.write("Generate and run Selenium Java test cases with LLM + POM support")

# Ensure cache directory exists for memory persistence
os.makedirs("cache", exist_ok=True)
os.makedirs("rag_versions", exist_ok=True)  # For RAG version control
memory = MemoryManager()
cache = IntentCache()

# Session state setup
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "generated_intent" not in st.session_state:
    st.session_state.generated_intent = ""
if "generated_code_ready" not in st.session_state:
    st.session_state.generated_code_ready = False
if "multi_module_specs" not in st.session_state:
    st.session_state.multi_module_specs = []
if "llm_response_time" not in st.session_state:
    st.session_state.llm_response_time = ""

# ----- Sidebar Configuration -----
with st.sidebar:
    st.header("Test Setup")
    env_choice = st.selectbox("Environment", ["production", "qa", "stage"], index=0)
    custom_url = st.text_input("Override URL (optional)", "")
    browser_choice = st.selectbox("Browser", ["chrome", "firefox"], index=0)
    use_browserstack = st.checkbox("Run on BrowserStack?", False)

    llm_choice = st.radio("LLM Mode", ["local", "openai"], index=0)
    if llm_choice == "local":
        previous_model = st.session_state.get("local_model_name", "")
        local_model_name = st.selectbox("Local Model", [
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "teknium/OpenHermes-2.5-Mistral-7B",
            "mistralai/Mistral-7B-Instruct-v0.2"
        ], index=0)

        if local_model_name != previous_model or "last_loaded_model" not in st.session_state:
            st.session_state.local_model_name = local_model_name
            with st.spinner(f"🧠 Loading model: {local_model_name}... please wait"):
                success = initialize_local_model()
            if success:
                st.session_state["last_loaded_model"] = local_model_name
                st.toast(f"✅ Loaded model: {local_model_name}", icon="🧠")
            else:
                st.error(f"❌ Failed to load model: {local_model_name}")
        else:
            st.info(f"✅ Model already loaded: {local_model_name}")


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
            if "chat_history" in st.session_state:
                del st.session_state["chat_history"]
            st.success("Memory cleared! Chat and test prompt history reset.")
            st.session_state.memory_exported = False
            st.rerun()

    st.subheader("📄 RAG Setup: Help Docs")
    uploaded_file = st.file_uploader("Upload Help PDF", type="pdf")
    doc_url = st.text_input("Or Enter Help Page URL")

    if st.button("📥 Ingest Help Docs"):
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
        msg = cache.clear_cache()
        st.success(msg)

# Get target URL
target_url = custom_url if custom_url else get_target_url(env_choice)

# Chat Interface
st.subheader("🧠 Interactive Chat")
user_input = st.text_area("Describe your test case or ask for changes", "", height=100)
send_clicked = st.button("Send", disabled=not user_input.strip())

# Show LLM response time
# if st.session_state.llm_response_time:
#     st.markdown(f"⏱️ **LLM Response Time:** `{st.session_state.llm_response_time}` (hh:mm:ss:ms)")
def format_elapsed_time(start, end):
    elapsed = end_time - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)
    milliseconds = int((elapsed - int(elapsed)) * 1000)
    formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}:{milliseconds:03}"
    return formatted_time

def format_llm_elapsed_time(elapsed_seconds: float) -> str:
    hours = int(elapsed_seconds // 3600)
    minutes = int((elapsed_seconds % 3600) // 60)
    seconds = int(elapsed_seconds % 60)
    milliseconds = int((elapsed_seconds - int(elapsed_seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}:{milliseconds:03}"


# ==== MAIN CHAT SUBMISSION BLOCK ====
if send_clicked and user_input.strip():
    cached_code = cache.get_cached(user_input)
    if cached_code:
        st.success("♻️ Using previously generated test code from cache.")
        st.code(cached_code, language="java")

        # Save cached code to disk so it can be compiled and executed
        os.makedirs("generated_code/src/test/java/com/charitableimpact", exist_ok=True)
        java_file_path = os.path.join("generated_code/src/test/java/com/charitableimpact", "CachedTest.java")
        with open(java_file_path, "w") as f:
            f.write(cached_code)

        st.session_state.generated_code_ready = True
        st.info("✅ Cached code written to `generated_code/src/test/java/CachedTest.java` and ready to run.")
    else:
        with st.spinner("💬 Generating response from LLM..."):
            start_time = time.time()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.chat_history.append({"role": "user", "content": user_input, "timestamp": timestamp})

            if "@" in user_input and "/" in user_input:
                enriched_prompt = (
                    f"Using the credentials and default URL or target URL provided, login to the app and continue test case steps.\n"
                    f"Credentials are likely included in the user message. Target URL: {target_url}\n"
                    f"Generate proper Selenium+TestNG test code based on this instruction."
                )
                st.session_state.chat_history.append({"role": "system", "content": enriched_prompt})

            response, llm_response_time = chat_with_llm(st.session_state.chat_history)
            st.session_state.llm_response_time = f"{llm_response_time} sec"
            formatted_time = format_llm_elapsed_time(llm_response_time)
            st.metric(label="🧠 LLM Response Time", value=formatted_time)
            end_time = time.time()

            st.session_state.chat_history.append({"role": "assistant", "content": response, "timestamp": timestamp})
            memory.save_interaction(user_input, response)
            cache.store(user_input, response)

            def extract_multiple_modules_from_prompt(prompt):
                page_names = re.findall(r"\\b(\\w+)\\s+page", prompt, re.IGNORECASE)
                return [name.capitalize() for name in page_names] or ["Test"]

            def get_validation_string(validations):
                for key in ["label", "text", "name", "value"]:
                    if validations and key in validations[0]:
                        return validations[0][key]
                return None

            page_names = extract_multiple_modules_from_prompt(user_input)
            stored_classes = []

            for name in page_names:
                validation_url = target_url
                if "@" in user_input and "/" in user_input:
                    creds = re.findall(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]+\s*/\s*[^\s]+", user_input)
                    if creds:
                        username, password = creds[0].split("/")
                        dom_validations = suggest_validations_authenticated(validation_url, username.strip(), password.strip())
                    else:
                        dom_validations = suggest_validations(validation_url)
                else:
                    dom_validations = suggest_validations(validation_url)

                validation_string = get_validation_string(dom_validations)
                short_hash = hashlib.sha1((user_input + name).encode()).hexdigest()[:5]
                existing_names = [m["class_name"] for m in st.session_state.multi_module_specs]
                unique_class = name if name not in existing_names else f"{name}_{short_hash}"

                st.session_state.multi_module_specs.append({
                    "user_prompt": user_input,
                    "validations": dom_validations,
                    "url": validation_url,
                    "class_name": unique_class,
                    "validation_string": validation_string,
                    "browser": browser_choice
                })

                stored_classes.append(unique_class)

            st.balloons()
            st.success(f"✅ Stored modules: {', '.join(stored_classes)} (ready for generation)")

# Show queued modules
if st.session_state.multi_module_specs:
    st.markdown("### 🧾 Queued Modules:")
    for mod in st.session_state.multi_module_specs:
        st.markdown(f"- `{mod['class_name']}` for {mod['url']}")

# Button: Generate all test modules
generate_clicked = st.sidebar.button("🧪 Generate All Modules", disabled=not st.session_state.multi_module_specs)
if generate_clicked:
    with st.spinner("🔄 Generating all test modules..."):
        generate_multiple_tests(st.session_state.multi_module_specs)
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

# Button: Run tests
run_clicked = st.sidebar.button("✅ Run Test Now", disabled=not st.session_state.generated_code_ready)
if run_clicked:
    st.markdown("**📦 Packaging Maven project and starting WebDriver session...**")
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

# Extent report handling
if st.session_state.get("test_execution_complete", False):

    report_path = os.path.abspath("generated_code/generated_code/test-output/ExtentReport.html")

    # Wait for report to be written
    max_wait = 10  # seconds
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

        st.warning("🧾 Please open the downloaded report manually in your browser to view the full styled report.")
    else:
        st.warning("⚠️ Extent report not found. Check if test execution was successful.")