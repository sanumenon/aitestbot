from jinja2 import Template
import os

def load_template(name):
    with open(f"templates/{name}", "r") as f:
        return Template(f.read())

def generate_test_code(user_prompt, validations, url, browser="chrome"):
    os.makedirs("generated_code", exist_ok=True)
    files = {}

    # Page Object
    page_template = load_template("page_template.java.j2")
    page_code = page_template.render(elements=validations)
    files["LoginPage.java"] = page_code

    # Test Case (uses browser-aware template)
    test_template = load_template("test_template2.java.j2")
    test_code = test_template.render(url=url, browser=browser)
    files["LoginTest.java"] = test_code

    # POM.xml
    pom_template = load_template("pom.xml.j2")
    files["pom.xml"] = pom_template.render()

    # Write to disk
    for name, content in files.items():
        with open(f"generated_code/{name}", "w") as f:
            f.write(content)

    return files
