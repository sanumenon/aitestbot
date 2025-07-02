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

    # If no validation string provided, use the first element label
    if validation_string is None:
        validation_string = validations[0].get("label", "Welcome") if validations else "Welcome"

    # Normalize validations
    for v in validations:
        label = v.get("label", "element")
        v["name"] = v.get("name") or label.replace(" ", "_").lower()
    
        if v["name"] in {"class", "new", "default", "public", "private"}:
            v["name"] += "_field"
    
        element_type = v.get("type", "textbox").lower()

        # Normalize types
        if element_type in {"textarea", "commentbox"}:
            v["type"] = "textarea"
            v["is_textarea"] = True
        elif element_type in {"dropdown", "select"}:
            v["type"] = "dropdown"
            v["is_dropdown"] = True
        elif element_type in {"checkbox"}:
            v["type"] = "checkbox"
            v["is_checkbox"] = True
        elif element_type in {"radio", "radiobutton"}:
            v["type"] = "radiobutton"
            v["is_radiobutton"] = True
        elif element_type in {"button", "submit"}:
            v["type"] = "button"
            v["is_button"] = True
        else:
            v["type"] = "textbox"
            v["is_textbox"] = True

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
        validations=validations
    )
    files[f"{class_name}Test.java"] = test_code

    # Render POM
    files["pom.xml"] = pom_template.render()

    # File structure
    base_path = "generated_code/src/test/java/com/charitableimpact"
    os.makedirs(base_path, exist_ok=True)

    for name, content in files.items():
        print("Generating file:", name)
        output_path = f"{base_path}/{name}" if name.endswith(".java") else f"generated_code/{name}"
        with open(output_path, "w") as f:
            f.write(content)

    return files
