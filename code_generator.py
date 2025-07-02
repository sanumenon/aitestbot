from jinja2 import Template
import os

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

    # If not provided explicitly, try to infer it
    if validation_string is None:
        validation_string = validations[0].get("label", "Welcome") if validations else "Welcome"

    # ✅ Normalize validation data before rendering templates
    for v in validations:
        v["name"] = v.get("name") or v.get("label", "element").replace(" ", "_").lower()
        # Avoid Java reserved keywords in field names
        if v["name"] in {"class", "new", "default", "public", "private"}:
            v["name"] = v["name"] + "_field"
        v["type"] = v.get("type", "textbox")  # default to textbox if unknown

    # Render Java page object
    page_code = page_template.render(elements=validations, class_name=class_name)
    files[f"{class_name}Page.java"] = page_code

    # Render test class
    test_code = test_template.render(
        class_name=class_name,
        page_class=f"{class_name}Page",
        url=url,
        browser=browser,
        validation_string=validation_string,
        validations=validations  # Pass this if used in test_template too
    )
    files[f"{class_name}Test.java"] = test_code

    # Render pom.xml
    files["pom.xml"] = pom_template.render()
    base_path = "generated_code/src/test/java/com/charitableimpact"
    os.makedirs(base_path, exist_ok=True)

    for name, content in files.items():
        print("Generating file:", name)
        if name == "pom.xml":
            with open(f"generated_code/{name}", "w") as f:
                f.write(content)
        else:
            with open(f"{base_path}/{name}", "w") as f:
                f.write(content)

    return files
