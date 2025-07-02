from jinja2 import Template
import os
import keyword

JAVA_RESERVED_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "true", "false", "null"
}

def sanitize_name(name):
    name = name.replace(" ", "_").replace("-", "_").lower()
    if name in JAVA_RESERVED_KEYWORDS or keyword.iskeyword(name):
        return name + "_field"
    return name

def load_template(name):
    with open(f"templates/{name}", "r") as f:
        return Template(f.read())

def generate_test_code(user_prompt, validations, url, browser="chrome", class_name="Test", validation_string=None):
    os.makedirs("generated_code", exist_ok=True)
    files = {}

    # Load templates
    page_template = load_template("page_template.java.j2")
    test_template = load_template("test_template.java.j2")
    pom_template = load_template("pom.xml.j2")

    include_text_validation = bool(validation_string)

    # Normalize validations
    for v in validations:
        label = v.get("label", "element")
        v["name"] = v.get("name") or label.replace(" ", "_").lower()

        if v["name"] in JAVA_RESERVED_KEYWORDS:
            v["name"] += "_field"

        element_type = v.get("type", "textbox").lower()

        # Normalize types
        v["type"] = element_type
        v["is_textarea"] = element_type in {"textarea", "commentbox"}
        v["is_dropdown"] = element_type in {"dropdown", "select"}
        v["is_checkbox"] = element_type == "checkbox"
        v["is_radiobutton"] = element_type in {"radio", "radiobutton"}
        v["is_button"] = element_type in {"button", "submit"}
        v["is_textbox"] = not any([v["is_textarea"], v["is_dropdown"], v["is_checkbox"], v["is_radiobutton"], v["is_button"]])

    # Render Java Page Object
    page_code = page_template.render(
        elements=validations,
        class_name=class_name
    )
    files[f"{class_name}Page.java"] = page_code

    # Render Test Class
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

    # Render POM
    files["pom.xml"] = pom_template.render()

    # Write files
    base_path = "generated_code/src/test/java/com/charitableimpact"
    os.makedirs(base_path, exist_ok=True)

    for name, content in files.items():
        print("Generating file:", name)
        output_path = f"{base_path}/{name}" if name.endswith(".java") else f"generated_code/{name}"
        with open(output_path, "w") as f:
            f.write(content)

    return files
def generate_multiple_tests(test_specs):
    """
    Accepts a list of test module specs like:
    [
        {
            "user_prompt": "Login form",
            "validations": [...],
            "url": "https://my.charitableimpact.com/login",
            "class_name": "Login",
            "validation_string": "Welcome"
        },
        {
            "user_prompt": "Dashboard interactions",
            "validations": [...],
            "url": "https://my.chariabtleimpact.com/dashboard",
            "class_name": "Dashboard",
            "validation_string": "Dashboard loaded"
        }
    ]
    """
    for spec in test_specs:
        print(f"🔧 Generating test class for: {spec['class_name']}")
        generate_test_code(
            user_prompt=spec.get("user_prompt", ""),
            validations=spec["validations"],
            url=spec["url"],
            browser=spec.get("browser", "chrome"),
            class_name=spec["class_name"],
            validation_string=spec.get("validation_string")
        )

