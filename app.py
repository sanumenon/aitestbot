# app.py
import streamlit as st
from config import get_target_url, DEFAULT_BROWSER
from llm_engine import chat_with_llm, set_llm_mode
from memory_manager import MemoryManager
from code_generator import generate_test_code, generate_multiple_tests
from dom_scraper import suggest_validations
from executor import execute_tests_live
from tinydb import TinyDB
import os
import json
from datetime import datetime
import re
import time
import subprocess
import hashlib

# Set Streamlit UI layout and title
st.set_page_config(page_title="AI Test Bot for Charitable Impact", layout="wide")
st.title("🤖 AI Test Bot for Charitableimpact")
st.write("Generate and run Selenium Java test cases with LLM + POM support")

# Ensure cache directory exists for memory persistence
os.makedirs("cache", exist_ok=True)
memory = MemoryManager()

# Session state setup
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "generated_intent" not in st.session_state:
    st.session_state.generated_intent = ""
if "generated_code_ready" not in st.session_state:
    st.session_state.generated_code_ready = False
if "multi_module_specs" not in st.session_state:
    st.session_state.multi_module_specs = []

# ----- Sidebar Configuration -----
with st.sidebar:
    st.header("Test Setup")
    env_choice = st.selectbox("Environment", ["production", "qa", "stage"], index=0)
    custom_url = st.text_input("Override URL (optional)", "")
    browser_choice = st.selectbox("Browser", ["chrome", "firefox"], index=0)
    use_browserstack = st.checkbox("Run on BrowserStack?", False)

    llm_choice = st.radio("LLM Mode", ["local", "openai"], index=0)
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

# Get target URL
target_url = custom_url if custom_url else get_target_url(env_choice)

# Chat Interface
st.subheader("🧠 Interactive Chat")
user_input = st.text_area("Describe your test case or ask for changes", "", height=100)
send_clicked = st.button("Send", disabled=not user_input.strip())

# Helper: Extract class name from prompt
def extract_multiple_modules_from_prompt(prompt):
    page_names = re.findall(r"\b(\w+)\s+page", prompt, re.IGNORECASE)
    if not page_names:
        return ["Test"]  # fallback
    return [name.capitalize() for name in page_names]

# Helper: Get validation string from validations
def get_validation_string(validations):
    if not validations:
        return None
    for key in ["label", "text", "name", "value"]:
        if key in validations[0]:
            return validations[0][key]
    return None

# ==== MAIN CHAT SUBMISSION BLOCK ====
if send_clicked and user_input.strip():
    with st.spinner("💬 Generating response from LLM..."):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.chat_history.append({"role": "user", "content": user_input, "timestamp": timestamp})

        # Automatically embed credentials and URL if mentioned
        if "@" in user_input and "/" in target_url:
            enriched_prompt = (
                f"Using the credentials and default URL or target URL provided, login to the app and continue test case steps.\n"
                f"Credentials are likely included in the user message. Target URL: {target_url}\n"
                f"Generate proper Selenium+TestNG test code based on this instruction."
            )
            st.session_state.chat_history.append({"role": "system", "content": enriched_prompt})

        response = chat_with_llm(st.session_state.chat_history)
        st.session_state.chat_history.append({"role": "assistant", "content": response, "timestamp": timestamp})
        memory.save_interaction(user_input, response)

        page_names = extract_multiple_modules_from_prompt(user_input)
        stored_classes = []

        for name in page_names:
            validation_url = target_url
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

# Show editable chat history
st.markdown("### 💬 Chat History (Editable)")
for i, msg in enumerate(st.session_state.chat_history):
    key = f"msg_{i}"
    timestamp = msg.get("timestamp", "")
    label = f"[{timestamp}] User says:" if msg["role"] == "user" else f"[{timestamp}] AI response:"
    updated = st.text_area(label, msg["content"], key=key)
    st.session_state.chat_history[i]["content"] = updated

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

    st.session_state.generated_code_ready = False
