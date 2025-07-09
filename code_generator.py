#code_generator.py
from jinja2 import Template
import os
import keyword
from dom_scraper import suggest_validations_authenticated
from llm_engine import chat_with_llm
from rag_search import retrieve_context
import re

JAVA_RESERVED_KEYWORDS = {...}  # same as before

# --- Enhanced Prompt Splitter ---
def split_prompt_into_tasks(prompt: str) -> list:
    delimiters = [' and ', ' then ', '\n', '.', ',']
    for d in delimiters:
        prompt = prompt.replace(d, '|')
    return [p.strip() for p in prompt.split('|') if p.strip()]

def sanitize_name(name):
    name = name.replace(" ", "_").replace("-", "_").lower()
    if name in JAVA_RESERVED_KEYWORDS or keyword.iskeyword(name):
        return name + "_field"
    return name

def load_template(name):
    with open(f"templates/{name}", "r") as f:
        return Template(f.read())

def generate_test_code(user_prompt, validations, url, browser="chrome", class_name="Test", validation_string=None, llm_java_code=None):
    os.makedirs("generated_code", exist_ok=True)

    # ✅ STEP 1: If LLM returned complete code, write it as-is
    if llm_java_code:
        java_file = f"{class_name}Test.java"
        output_path = f"generated_code/src/test/java/com/charitableimpact/{java_file}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(llm_java_code)
        return {java_file: llm_java_code}

    # ✅ STEP 2: If no LLM code provided, fall back to template-based generation
    files = {}

    page_template = load_template("page_template.java.j2")
    test_template = load_template("test_template.java.j2")
    pom_template = load_template("pom.xml.j2")

    include_text_validation = bool(validation_string)

    for v in validations:
        label = v.get("label", "element")
        v["name"] = v.get("name") or sanitize_name(label)
        v["type"] = v.get("type", "textbox").lower()
        v["is_textarea"] = v["type"] in {"textarea", "commentbox"}
        v["is_dropdown"] = v["type"] in {"dropdown", "select"}
        v["is_checkbox"] = v["type"] == "checkbox"
        v["is_radiobutton"] = v["type"] in {"radio", "radiobutton"}
        v["is_button"] = v["type"] in {"button", "submit"}
        v["is_textbox"] = not any([
            v["is_textarea"], v["is_dropdown"],
            v["is_checkbox"], v["is_radiobutton"],
            v["is_button"]
        ])
        v["by"] = "xpath"
        v["selector"] = v["xpath"]

    # Render the page object class
    page_code = page_template.render(elements=validations, class_name=class_name)
    files[f"{class_name}Page.java"] = page_code

    # Render the test class
    test_code = test_template.render(
        class_name=class_name,
        page_class=f"{class_name}Page",
        url=url,
        browser=browser,
        validation_string=validation_string,
        validations=validations,
        include_text_validation=include_text_validation
    )
    files[f"{class_name}Test.java"] = test_code

    # Render pom.xml
    files["pom.xml"] = pom_template.render()

    # Write files to disk
    base_path = "generated_code/src/test/java/com/charitableimpact"
    os.makedirs(base_path, exist_ok=True)

    for name, content in files.items():
        output_path = (
            f"{base_path}/{name}" if name.endswith(".java") else f"generated_code/{name}"
        )
        with open(output_path, "w") as f:
            f.write(content)

    return files

def generate_multiple_tests(module_specs: list):
    for mod in module_specs:
        user_prompt = mod.get("user_prompt", "")
        validations = mod.get("validations", [])
        url = mod.get("url", "")
        class_name = mod.get("class_name", "Test")
        validation_string = mod.get("validation_string", None)
        browser = mod.get("browser", "chrome")
        llm_code = mod.get("llm_java_code", None)
        generate_test_code(
            user_prompt=user_prompt,
            validations=validations,
            url=url,
            browser=browser,
            class_name=class_name,
            validation_string=validation_string,
            llm_java_code=llm_code
        )

def generate_multiple_tests_from_prompt(user_prompt, url, username=None, password=None, browser="chrome", log_callback=print):
    tasks = split_prompt_into_tasks(user_prompt)
    all_generated = []

    for i, task in enumerate(tasks):
        log_callback(f"⏳ Generating test {i+1}/{len(tasks)}: {task}")

        context = retrieve_context(task)
        full_prompt = (
            f"{context}\n\n"
            f"You are testing charitableimpact.com. "
            f"Generate Java Selenium 4.2+ TestNG code using Page Object Model. "
            f"If the task implies a new page or screen, create a new Page and Test class. "
            f"Each test must be independent, follow proper functional flow, and avoid hardcoded driver paths.\n"
            f"Task: {task}"
        )

        chat_history = [{"role": "user", "content": full_prompt}]
        llm_code, llm_time = chat_with_llm(chat_history)

        test_methods = re.findall(r'@Test\s+public void\s+(\w+)\s*\(\)\s*\{.*?\}', llm_code, re.DOTALL)

        class_name = re.sub(r'[^a-zA-Z0-9]', '', task.title().replace(" ", "")) or f"Task{i+1}"

        validations = suggest_validations_authenticated(url, username, password)
        validation_string = "Success" if validations else None

        file_map = generate_test_code(
            user_prompt=task,
            validations=validations,
            url=url,
            browser=browser,
            class_name=class_name,
            validation_string=validation_string,
            llm_java_code=llm_code
        )

        log_callback(f"✅ Generated files: {', '.join(file_map.keys())}")

        all_generated.append({
            "class_name": class_name,
            "test_methods": test_methods,
            "llm_time": llm_time
        })

    return all_generated
