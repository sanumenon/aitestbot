# app.py
import streamlit as st
from config import get_target_url, DEFAULT_BROWSER
from llm_engine import chat_with_llm, set_llm_mode
from memory_manager import MemoryManager
from code_generator import generate_test_code
from dom_scraper import suggest_validations
from executor import execute_tests_live
from tinydb import TinyDB
import os
import json
from datetime import datetime
import re
import time
import subprocess

# Set Streamlit UI layout and title
st.set_page_config(page_title="AI Test Bot for Charitable Impact", layout="wide")
st.title("🤖 AI Test Bot for Charitableimpact")
st.write("Generate and run Selenium Java test cases with LLM + POM support")

# Ensure cache directory exists for memory persistence
os.makedirs("cache", exist_ok=True)
memory = MemoryManager()

# ----- Sidebar Configuration -----
with st.sidebar:
    st.header("Test Setup")
    env_choice = st.selectbox("Environment", ["production", "qa", "stage"], index=0)
    custom_url = st.text_input("Override URL (optional)", "")
    browser_choice = st.selectbox("Browser", ["chrome", "firefox"], index=0)
    use_browserstack = st.checkbox("Run on BrowserStack?", False)

    llm_choice = st.radio("LLM Mode", ["local", "openai"], index=0)
    set_llm_mode(llm_choice)  # Pass the selected mode to llm_engine

    # Memory management options
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

# Decide which environment URL to test against
target_url = custom_url if custom_url else get_target_url(env_choice)

# ----- Chat Interface -----
st.subheader("🧠 Interactive Chat")
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "generated_intent" not in st.session_state:
    st.session_state.generated_intent = ""
if "generated_code_ready" not in st.session_state:
    st.session_state.generated_code_ready = False

user_input = st.text_area("Describe your test case or ask for changes", "", height=100)
send_clicked = st.button("Send", disabled=not user_input.strip())

if send_clicked and user_input.strip():
    with st.spinner("💬 Generating response from LLM..."):
        st.markdown("**⏳ Preparing prompt...**")
        time.sleep(0.5)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.chat_history.append({"role": "user", "content": user_input, "timestamp": timestamp})

        st.markdown("**📱 Sending chat to LLM...**")
        time.sleep(0.5)
        response = chat_with_llm(st.session_state.chat_history)

        st.markdown("**🧠 LLM response received. Saving memory...**")
        time.sleep(0.5)
        st.session_state.chat_history.append({"role": "assistant", "content": response, "timestamp": timestamp})
        memory.save_interaction(user_input, response)
        st.session_state.generated_intent = user_input
        st.session_state.generated_code_ready = False  # Reset flag after new prompt

        st.balloons()
        st.success("✅ Response from LLM received!")

# Show editable chat history with timestamps
st.markdown("### 💬 Chat History (Editable)")
for i, msg in enumerate(st.session_state.chat_history):
    key = f"msg_{i}"
    timestamp = msg.get("timestamp", "")
    label = f"[{timestamp}] User says:" if msg["role"] == "user" else f"[{timestamp}] AI response:"
    updated = st.text_area(label, msg["content"], key=key)
    st.session_state.chat_history[i]["content"] = updated

# Extract a class name for the test case based on user prompt
def extract_class_name_from_prompt(prompt):
    match = re.search(r"\b(?:for|to|on)\s+(\w+)(?:\s+page)?", prompt, re.IGNORECASE)
    if match:
        return match.group(1).capitalize()
    return "Test"

# ----- Code Generation Block -----
generate_clicked = st.sidebar.button("✅ Generate Test Case", disabled=not st.session_state.generated_intent)
if generate_clicked:
    if st.session_state.generated_intent:
        with st.spinner("🛠 Generating test code and validations..."):
            st.markdown("**🔍 Scraping UI DOM and generating validation logic...**")
            dom_validations = suggest_validations(target_url)
            class_name = extract_class_name_from_prompt(st.session_state.generated_intent)

            st.markdown("**🧱 Rendering templates and writing Java code...**")

            def get_validation_string(validations):
                if not validations:
                    return "Welcome"
                possible_keys = ["label", "text", "name", "value"]
                for key in possible_keys:
                    if key in validations[0]:
                        return validations[0][key]
                return "Welcome"

            validation_string = get_validation_string(dom_validations)

            java_files = generate_test_code(
                st.session_state.generated_intent,
                dom_validations,
                target_url,
                browser_choice,
                class_name,
                validation_string=validation_string
            )

            st.subheader("🛠 Generated Files")
            for name, content in java_files.items():
                st.text(f"{name}")
                st.code(content, language='java')

            st.success("Test code generated successfully!")
            st.session_state.generated_code_ready = True
    else:
        st.warning("Please interact with the chatbot to describe what test case to generate.")

# ----- Run Test Block -----
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
    # DO NOT call st.rerun() here to prevent log flicker