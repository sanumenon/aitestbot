# app.py
import streamlit as st
from config import get_target_url, DEFAULT_BROWSER
from llm_engine import chat_with_llm
from memory_manager import MemoryManager
from code_generator import generate_test_code
from dom_scraper import suggest_validations
from executor import execute_tests
from tinydb import TinyDB
import os
import json
from datetime import datetime
import re

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

    # Enable/Disable buttons based on chat + code status
    generate_code = st.button("Generate Test Case", disabled="generated_intent" not in st.session_state)
    run_test = st.button("Run Test Now", disabled="generated_code_ready" not in st.session_state)

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
            st.experimental_rerun()

# Decide which environment URL to test against
target_url = custom_url if custom_url else get_target_url(env_choice)

# ----- Chat Interface -----
st.subheader("🧠 Interactive Chat")
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.text_area("Describe your test case or ask for changes", "", height=100)
send_clicked = st.button("Send", disabled=not user_input.strip())

if send_clicked and user_input.strip():
    with st.spinner("💬 Generating response from LLM..."):
        st.markdown("**⏳ Preparing prompt, querying LLM and saving memory...**")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.chat_history.append({"role": "user", "content": user_input, "timestamp": timestamp})
        response = chat_with_llm(st.session_state.chat_history)
        st.session_state.chat_history.append({"role": "assistant", "content": response, "timestamp": timestamp})
        memory.save_interaction(user_input, response)
        st.session_state.generated_intent = user_input
        st.session_state.generated_code_ready = False  # Reset flag after new prompt

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
if generate_code:
    if "generated_intent" in st.session_state:
        with st.spinner("🛠 Generating test code and validations..."):
            st.markdown("**🔍 Scraping UI DOM and generating validation logic...**")
            dom_validations = suggest_validations(target_url)
            class_name = extract_class_name_from_prompt(st.session_state.generated_intent)

            st.markdown("**🧱 Rendering templates and writing Java code...**")
            java_files = generate_test_code(
                st.session_state.generated_intent,
                dom_validations,
                target_url,
                browser_choice,
                class_name
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
if run_test and st.session_state.get("generated_code_ready"):
    with st.spinner("🚀 Executing test on selected browser..."):
        st.markdown("**📦 Packaging Maven project and starting WebDriver session...**")
        logs = execute_tests(browser_choice, use_browserstack)
        st.subheader("🚀 Test Execution Logs")
        st.code(logs, language='bash')
        st.success("Test execution completed!")
        st.session_state.generated_code_ready = False  # Reset flag after execution
