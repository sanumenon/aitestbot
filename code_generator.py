from jinja2 import Template
import os
import keyword
from dom_scraper import suggest_validations_authenticated
from llm_engine import chat_with_llm
from rag_search import retrieve_context
import re

JAVA_RESERVED_KEYWORDS = {...}  # same as before

import re

TEST_CLASS_IMPORTS = """
import org.openqa.selenium.*;
import org.openqa.selenium.chrome.*;
import io.github.bonigarcia.wdm.WebDriverManager;
import org.testng.*;
import org.testng.annotations.*;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.testng.Assert;
import org.testng.asserts.SoftAssert;
import com.aventstack.extentreports.*;
import com.charitableimpact.config.ExtentReportManager;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.By;
import java.time.Duration;
"""

PAGE_CLASS_IMPORTS = """
import org.openqa.selenium.*;
import org.openqa.selenium.support.*;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.By;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.Select;
import org.openqa.selenium.interactions.Actions;
import java.time.Duration;
"""
def get_required_imports(is_test_class: bool) -> str:
    return TEST_CLASS_IMPORTS if is_test_class else PAGE_CLASS_IMPORTS


def fix_generated_code_errors(code: str) -> str:
    # 🔧 Replace forbidden ExtentReportManager.getExtent() calls
    code = re.sub(
        r'ExtentReportManager\.getExtent\s*\(\s*\)',
        'ExtentReportManager.createTest("TestName")',
        code
    )

    # ✅ Ensure required WebDriverManager import is present
    if 'WebDriverManager.' in code and 'io.github.bonigarcia.wdm.WebDriverManager' not in code:
        code = 'import io.github.bonigarcia.wdm.WebDriverManager;\n' + code

    # ✅ Ensure required ExtentReport imports if ExtentTest or Status used
    if 'ExtentTest' in code or 'Status.' in code:
        required_imports = [
            'import com.aventstack.extentreports.ExtentReports;',
            'import com.aventstack.extentreports.ExtentTest;',
            'import com.aventstack.extentreports.Status;',
            'import com.charitableimpact.config.ExtentReportManager;',
        ]
        for imp in reversed(required_imports):
            if imp not in code:
                code = imp + "\n" + code

    return code


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

def strip_duplicate_imports(java_code):
    seen = set()
    result = []
    for line in java_code.splitlines():
        if line.strip().startswith("import"):
            if line.strip() not in seen:
                result.append(line)
                seen.add(line.strip())
        else:
            result.append(line)
    return "\n".join(result)

def convert_to_findby(code):
    pattern = re.compile(r'driver\.findElement\(By\.(\w+)\("(.*?)"\)\)')
    replacements = {
        'id': '@FindBy(id="{val}")',
        'xpath': '@FindBy(xpath="{val}")',
        'cssSelector': '@FindBy(css="{val}")',
        'name': '@FindBy(name="{val}")'
    }
    lines = code.splitlines()
    output = []
    for line in lines:
        match = pattern.search(line)
        if match:
            by_type, value = match.group(1), match.group(2)
            if by_type in replacements:
                annotation = replacements[by_type].format(val=value)
                output.append(f"    {annotation}")
                output.append(f"    private WebElement {value.replace('-', '_')};")
                continue
        output.append(line)
    return "\n".join(output)



### ✅ How to Fix (Defensive Extraction Strategy)

def extract_classes_from_llm_code(llm_java_code):
    llm_java_code = llm_java_code.strip().replace("\r\n", "\n")

    # 🔁 Normalize common variants
    llm_java_code = re.sub(r"(?i)^===\s*(page|test)\s*object\s*class\s*:", r"=== \1 OBJECT CLASS:", llm_java_code, flags=re.MULTILINE)
    llm_java_code = re.sub(r"(?i)^===\s*(page|test)\s*class\s*:", r"=== \1 OBJECT CLASS:", llm_java_code, flags=re.MULTILINE)

    marker_pattern = r"(?i)==+\s*(page|test)\s*object\s*class\s*:\s*([a-zA-Z0-9_]+)\s*==+\s*```(?:java)?\s*\n(.*?)```"
    matches = re.findall(marker_pattern, llm_java_code, re.DOTALL)

    # 🧪 Logging
    print(f"🧪 Extracted {len(matches)} class blocks from LLM.")
    for ctype, cname, body in matches:
        first_line = body.strip().splitlines()[0] if body.strip().splitlines() else "[EMPTY]"
        print(f"  - {ctype.upper()} CLASS: {cname}, First line: {first_line}")

    # 🛡️ Defensive fallback if only one match found
    if len(matches) == 1:
        print("⚠️ Only one class block found. Trying fallback parse...")
        class_blocks = re.findall(r'```java\n(.*?)\n```', llm_java_code, re.DOTALL)
        if len(class_blocks) > 1:
            used_names = [m[1] for m in matches]
            for code_block in class_blocks:
                if not any(name in code_block for name in used_names):
                    inferred_name_match = re.search(r'public\s+class\s+([A-Za-z0-9_]+)', code_block)
                    if inferred_name_match:
                        name = inferred_name_match.group(1)
                        inferred_type = "test" if "Test" in name else "page"
                        print(f"🛠️ Fallback captured: {inferred_type.upper()} CLASS: {name}")
                        matches.append((inferred_type, name, code_block.strip()))
    return matches


def generate_test_code(user_prompt, validations, url, browser="chrome", class_name="Test", validation_string=None, llm_java_code=None):
    os.makedirs("generated_code", exist_ok=True)
    file_map = {}

    if llm_java_code:
        try:
            os.makedirs("generated_code/src/test/java/com/charitableimpact", exist_ok=True)

            matches = extract_classes_from_llm_code(llm_java_code)

            if not matches:
                print("❌ No classes extracted from LLM code. First 500 chars of response:")
                print(llm_java_code[:500])

            for class_type, class_name_found, class_body in matches:
                file_path = f"generated_code/src/test/java/com/charitableimpact/{class_name_found}.java"
                clean_code = re.sub(r"[^\x20-\x7E\n\t]", "", class_body.strip())
                clean_code = re.sub(r"^[-=]{3,}$", "", clean_code, flags=re.MULTILINE).strip()

                is_test_class = class_type.strip().lower() == "test"
                required_imports = get_required_imports(is_test_class).strip().splitlines()
                existing_imports = set(re.findall(r'^import\s+.*?;', clean_code, re.MULTILINE))
                new_imports = [imp for imp in required_imports if imp not in existing_imports]
                if new_imports:
                    clean_code = "\n".join(new_imports) + "\n" + clean_code


                if not is_test_class:
                    clean_code = convert_to_findby(clean_code)
                    if "PageFactory.initElements" not in clean_code:
                        clean_code = re.sub(
                            rf'(public\s+{class_name_found}\s*\(.*?\)\s*\{{)',
                            r'\1\n        PageFactory.initElements(driver, this);',
                            clean_code
                        )

                clean_code = strip_duplicate_imports(clean_code)

                with open(file_path, "w") as f:
                    fixed_code = fix_generated_code_errors(f"package com.charitableimpact;\n\n{clean_code}")
                    f.write(fixed_code)


                file_map[f"{class_name_found}.java"] = fixed_code

            return file_map

        except Exception as e:
            print(f"⚠️ Failed to write LLM code. Falling back to template. Error: {e}")

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
        v["selector"] = v.get("xpath") or v.get("selector") or v.get("css") or "//UNKNOWN"


    page_code = page_template.render(elements=validations, class_name=class_name)
    files[f"{class_name}Page.java"] = page_code

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
    files["pom.xml"] = pom_template.render()

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
        llm_code = mod.get("llm_code", None)
        generate_test_code(
            user_prompt=user_prompt,
            validations=validations,
            url=url,
            browser=browser,
            class_name=class_name,
            validation_string=validation_string,
            llm_java_code=llm_code
        )
