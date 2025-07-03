from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re


def sanitize_name(name):
    name = re.sub(r'\W+', '_', name)
    if not name or not name[0].isalpha():
        name = f"element_{name}"
    return name.lower()


def suggest_validations(url):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    driver.get(url)

    raw_elements = driver.find_elements(By.XPATH, "//input | //textarea | //select | //button")
    validations = []
    seen_names = set()

    for i, el in enumerate(raw_elements):
        try:
            if not el.is_displayed() or not el.is_enabled():
                continue

            tag = el.tag_name
            raw_name = el.get_attribute("name") or el.get_attribute("id") or el.get_attribute("placeholder") or f"element{i}"
            safe_name = sanitize_name(raw_name)

            while safe_name in seen_names:
                safe_name += f"_{i}"
            seen_names.add(safe_name)

            id_attr = el.get_attribute("id")
            xpath = driver.execute_script("""
                function absoluteXPath(element) {
                    const idx = (sib, name) => sib
                      ? idx(sib.previousElementSibling, name || sib.localName) + (sib.localName == name)
                      : 1;
                    const segs = elm => !elm || elm.nodeType !== 1
                      ? ['']
                      : elm.id && document.getElementById(elm.id) === elm
                      ? [`id(\"${elm.id}\")`]
                      : [...segs(elm.parentNode), `${elm.localName.toLowerCase()}[${idx(elm)}]`];
                    return segs(element).join('/');
                }
                return absoluteXPath(arguments[0]);
            """, el)

            if tag in ["input", "textarea"]:
                action = "enterText"
                sample_text = "sample input"
                element_type = "textarea" if tag == "textarea" else "textbox"
            elif tag in ["button"]:
                action = "click"
                sample_text = ""
                element_type = "button"
            elif tag in ["select"]:
                action = "select"
                sample_text = ""
                element_type = "dropdown"
            else:
                action = "click"
                sample_text = ""
                element_type = "button"

            validations.append({
                "name": safe_name,
                "xpath": f"//*[@id='{id_attr}']" if id_attr else xpath,
                "action": action,
                "sampleText": sample_text,
                "type": element_type,
                "label": raw_name.strip()
            })

        except Exception:
            continue

    driver.quit()
    return validations

def suggest_validations_authenticated(url, username, password):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    driver.get(url)

    try:
        # Basic login flow using common selectors (customize as needed)
        user_input = driver.find_element(By.XPATH, "//input[@type='email' or contains(@name, 'user')]")
        pass_input = driver.find_element(By.XPATH, "//input[@type='password']")
        login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log in') or @type='submit']")

        user_input.send_keys(username)
        pass_input.send_keys(password)
        login_btn.click()

        time.sleep(2)  # wait for login to process
    except Exception as e:
        print(f"⚠️ Login failed or not needed: {e}")

    validations = suggest_validations(driver.current_url)
    driver.quit()
    return validations

