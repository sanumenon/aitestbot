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
    "local_model_name": "google/gemma-2b"
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

def is_out_of_scope(prompt: str) -> bool:
    keywords = [
        "charitableimpact", "selenium", "testng", "java", "automation", "pom", "maven",
        "qa test", "login page", "signup flow", "browser automation", "test case"
    ]
    prompt_lower = prompt.lower()
    return not any(kw in prompt_lower for kw in keywords)


# Prevent multiple initializations
# if "initialized" not in st.session_state:
#     st.session_state.initialized = True   

#     st.set_page_config(page_title="AI Test Bot for Charitable Impact", layout="wide")
#     st.title("🤖 AI Test Bot for Charitableimpact")
#     st.write("Generate and run Selenium Java test cases with LLM + POM support")

#     os.makedirs("cache", exist_ok=True)
#     os.makedirs("rag_versions", exist_ok=True)


#     if "chat_history" not in st.session_state:
#         st.session_state.chat_history = []
#     if "generated_intent" not in st.session_state:
#         st.session_state.generated_intent = ""
#     if "generated_code_ready" not in st.session_state:
#         st.session_state.generated_code_ready = False
#     # if "multi_module_specs" not in st.session_state:
#     #     st.session_state.get("multi_module_specs", []) = []
#     if "llm_response_time" not in st.session_state:
#         st.session_state.llm_response_time = ""
#     if "local_model_loaded_once" not in st.session_state:
#         st.session_state.local_model_loaded_once = False
#     if "last_loaded_model" not in st.session_state:
#         st.session_state.last_loaded_model = ""

# Sidebar rendering
with st.sidebar:
    st.header("Test Setup")
    env_choice = st.selectbox("Environment", ["production", "qa", "stage"], index=0)
    custom_url = st.text_input("Override URL (optional)", "")
    browser_choice = st.selectbox("Browser", ["chrome", "firefox"], index=0)
    use_browserstack = st.checkbox("Run on BrowserStack?", False)

    llm_choice = st.radio("LLM Mode", ["local", "openai"], index=0)

    if llm_choice == "local":
        if "local_model_name" not in st.session_state:
            st.session_state.local_model_name = "google/gemma-2b"

        st.selectbox("Local Model", [
            "google/gemma-2b",
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "teknium/OpenHermes-2.5-Mistral-7B",
            "mistralai/Mistral-7B-Instruct-v0.2"
        ], key="local_model_name")

    local_model_name = st.session_state.local_model_name  # ✅ pull it back

    if not local_model_name.strip():
        st.error("⚠️ No model name selected. Please choose a valid local model.")
    elif (not st.session_state.local_model_loaded_once) or (st.session_state.last_loaded_model != local_model_name):
        with st.spinner(f"🧠 Loading model: {local_model_name}... please wait"):
            success = initialize_local_model(local_model_name)
        if success:
            st.session_state["last_loaded_model"] = local_model_name
            st.session_state["local_model_loaded_once"] = True
            st.toast(f"✅ Loaded model: {local_model_name}", icon="🧠")
        else:
            st.error(f"❌ Failed to load model: {local_model_name}")
    else:
        st.info(f"✅ Model already loaded: {local_model_name}")


    # Only set LLM mode if changed
    if st.session_state.get("llm_choice") != llm_choice:
        st.session_state["llm_choice"] = llm_choice
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
            last_model = st.session_state.get("last_loaded_model")
            model_loaded_flag = st.session_state.get("local_model_loaded_once")
            if os.path.exists("cache/memory.json"):
                db = TinyDB("cache/memory.json")
                db.truncate()
            for key in [
                "chat_history", "generated_intent", "generated_code_ready",
                "multi_module_specs", "llm_response_time", "memory_exported"
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            for key, default in required_session_keys.items():
                if key not in st.session_state:
                    st.session_state[key] = default

            st.session_state["last_loaded_model"] = last_model
            st.session_state["local_model_loaded_once"] = model_loaded_flag
            st.success("Memory cleared! Chat and test prompt history reset.")

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
        st.session_state["last_loaded_model"] = last_model
        st.session_state["local_model_loaded_once"] = model_loaded_flag

# Final fallback: Ensure LLM mode and default model applied once
if st.session_state.get("llm_choice") and not st.session_state.get("_llm_set_once"):
    if st.session_state["llm_choice"] == "openai":
        set_llm_mode("openai")
    elif st.session_state["llm_choice"] == "local":
        default_model = st.session_state.get("last_loaded_model", "google/gemma-2b")
        if not st.session_state.get("local_model_loaded_once"):
            with st.spinner(f"🧠 Auto-loading default model: {default_model}"):
                success = initialize_local_model(default_model)
            if success:
                st.session_state["last_loaded_model"] = default_model
                st.session_state["local_model_loaded_once"] = True
                st.toast(f"✅ Loaded model: {default_model}", icon="🧠")
            else:
                st.error(f"❌ Failed to load model: {default_model}")
    st.session_state["_llm_set_once"] = True




# Get target URL
target_url = custom_url if custom_url else get_target_url(env_choice)

# Chat Interface
st.subheader("🧠 Interactive Chat")
user_input = st.text_area("Describe your test case or ask for changes", "", height=100)
send_clicked = st.button("Send", disabled=not user_input.strip())

def format_elapsed_time(start_time, end_time):
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
def process_user_prompt(user_input: str):
    cached_code = cache.get_cached(user_input)
    if cached_code:
        st.success("♻️ Using previously generated test code from cache.")
        st.code(cached_code, language="java")

        os.makedirs("generated_code/src/test/java/com/charitableimpact", exist_ok=True)
        java_file_path = os.path.join("generated_code/src/test/java/com/charitableimpact", "CachedTest.java")
        with open(java_file_path, "w") as f:
            f.write(cached_code)

        st.session_state.generated_code_ready = True
        st.info("✅ Cached code written to `generated_code/src/test/java/CachedTest.java` and ready to run.")
        short_hash = hashlib.sha1((user_input).encode()).hexdigest()[:5]
        class_name = f"CachedTest_{short_hash}"
        if class_name not in [mod['class_name'] for mod in st.session_state.get("multi_module_specs", [])]:
            st.session_state.get("multi_module_specs", []).append({
                "user_prompt": user_input,
                "validations": [],
                "url": target_url,
                "class_name": class_name,
                "validation_string": None,
                "browser": browser_choice
            })
        return

    with st.spinner("💬 Generating response from LLM..."):
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if is_out_of_scope(user_input):
            response = "❌ I can only help with test case generation for charitableimpact.com using Java + Selenium + TestNG + Maven."
            st.markdown("#### 🤖 LLM Response")
            st.code(response, language="markdown")
            st.session_state.chat_history.append({"role": "assistant", "content": response, "timestamp": timestamp})
            memory.save_interaction(user_input, response)
            cache.store(user_input, response)
            return

        st.session_state.chat_history.append({"role": "user", "content": user_input, "timestamp": timestamp})

        if "@" in user_input and "/" in user_input:
            enriched_prompt = (
                f"Using the credentials and default URL or target URL provided, login to the app and continue test case steps.\n"
                f"Credentials are likely included in the user message. Target URL: {target_url}\n"
                f"Generate proper Selenium+TestNG test code based on this instruction."
            )
            st.session_state.chat_history.append({"role": "system", "content": enriched_prompt})
        st.info(f"🤖 LLM Mode in Use: {llm_choice}")

        response, llm_response_time = chat_with_llm(st.session_state.chat_history)
        llm_code = response
        end_time = time.time()

        st.code(response, language="java" if "class" in response else "markdown")
        st.markdown(f"🔍 Response generated by: `{llm_choice}` model")

        formatted_time = format_llm_elapsed_time(llm_response_time)
        st.metric(label="🧠 LLM Response Time", value=formatted_time)
        end_time = time.time()

        st.session_state.chat_history.append({"role": "assistant", "content": response, "timestamp": timestamp})
        st.markdown("#### 🤖 LLM Response")
        st.code(response, language="java" if "class" in response else "markdown")

        memory.save_interaction(user_input, response)
        cache.store(user_input, response)

        def extract_multiple_modules_from_prompt(prompt):
            page_names = re.findall(r"\b(\w+)\s+page", prompt, re.IGNORECASE)
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
            existing_names = [m["class_name"] for m in st.session_state.get("multi_module_specs", [])]
            unique_class = name if name not in existing_names else f"{name}_{short_hash}"

            st.session_state.get("multi_module_specs", []).append({
                "user_prompt": user_input,
                "validations": dom_validations,
                "url": validation_url,
                "class_name": unique_class,
                "validation_string": validation_string,
                "browser": browser_choice,
                "llm_code": llm_code
            })

            stored_classes.append(unique_class)

        st.balloons()
        st.success(f"✅ Stored modules: {', '.join(stored_classes)} (ready for generation)")

# And now the call:
if send_clicked and user_input.strip():
    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"📩 **Send clicked at:** {click_time}")
    process_user_prompt(user_input)
    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
run_clicked = st.sidebar.button("✅ Run Test Now", disabled=not st.session_state.generated_code_ready)
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
