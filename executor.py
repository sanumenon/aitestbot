# executor.py
import subprocess

def execute_tests(browser="chrome", use_browserstack=False):
    cmd = ["mvn", "clean", "test"]
    try:
        proc = subprocess.run(cmd, cwd="generated_code", capture_output=True, text=True)
        return proc.stdout + proc.stderr
    except Exception as e:
        return str(e)
