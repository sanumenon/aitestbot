#executor.py
import subprocess
import streamlit as st

def execute_tests_live(cwd="generated_code", browser="chrome", use_browserstack=False):
    st.markdown("**📦 Packaging Maven project and starting WebDriver session...**")
    log_box = st.empty()

    full_log = ""
    try:
        # Build Maven command
        mvn_cmd = ["mvn", "clean", "test", "-U", "-DsuiteXmlFile=testng.xml"]
        
        # Optional: pass browserstack flag to tests
        if use_browserstack:
            mvn_cmd.append("-Dbrowserstack=true")
        else:
            mvn_cmd.append(f"-Dbrowser={browser}")

        process = subprocess.Popen(
            mvn_cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Live stream the logs
        for line in iter(process.stdout.readline, ''):
            full_log += line
            log_box.code(full_log, language="bash")

        process.stdout.close()
        process.wait()

        if process.returncode != 0:
            st.error("❌ Maven test execution failed.")
        else:
            st.success("✅ Maven test execution completed.")

        return full_log

    except Exception as e:
        error_msg = f"❌ Error during Maven execution: {e}"
        st.error(error_msg)
        return error_msg
