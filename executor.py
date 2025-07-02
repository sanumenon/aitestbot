# executor.py
import subprocess
import streamlit as st

def execute_tests_live(cwd="generated_code", browser="chrome", use_browserstack=False):
    st.markdown("**📦 Packaging Maven project and starting WebDriver session...**")
    log_box = st.empty()

    try:
        process = subprocess.Popen(
           subprocess.run(["mvn", "clean", "test", "-U"]),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        full_log = ""
        for line in process.stdout:
            full_log += line
            log_box.code(full_log, language="bash")
        process.wait()
        return full_log
    except Exception as e:
        return f"❌ Error during execution: {e}"
