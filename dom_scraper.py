#dom_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# dom_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import re
import time
import pickle
import os

COOKIE_FILE = "cookies.pkl"


def sanitize_name(name):
    name = re.sub(r"[^\w]", "_", name)
    if not name or not name[0].isalpha():
        name = f"field_{name}"
    return name.lower()


def save_cookies_after_manual_login(url):
    print("🚀 Launching browser for manual login...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    driver.get(url)
    input("🔐 Complete login and press ENTER to save cookies...")
    with open(COOKIE_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
        print(f"✅ Cookies saved to {COOKIE_FILE}")
    driver.quit()


def load_browser_with_cookies(url):
    print("🚀 Launching browser with saved cookies...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    #modify here for env defaults scraping
    driver.get("https://charitableimpact.com")
    time.sleep(2)  # Let initial page load before setting cookies

    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                if "sameSite" in cookie:
                    del cookie["sameSite"]
                driver.add_cookie(cookie)
            print(f"✅ {len(cookies)} cookies loaded")
    else:
        print("⚠️ No cookie file found.")

    driver.get(url)  # Reload target page after cookies are injected
    return driver



def suggest_validations_with_bypass(url):
    driver = load_browser_with_cookies(url)
    print(f"🔄 Page loaded after bypass: {driver.current_url}")
    time.sleep(30)
    WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "input[id]"))
    )


    raw_elements = driver.find_elements(By.XPATH, """//input | //textarea | //select | //button | //*[@role='button'] | //a[@href] | //div[@role='button']""")

    validations = []
    seen_names = set()
    hydrated_ids = driver.execute_script("""
    return Array.from(document.querySelectorAll('input')).map(e => e.id);
    """)
    print(f"🧪 DEBUG: input IDs present in DOM: {hydrated_ids}")

    for i, el in enumerate(raw_elements):
        try:
            print("🧩 HTML:", el.get_attribute("outerHTML"))

            if not el.is_displayed() or not el.is_enabled():
                continue

            tag = el.tag_name
            input_type = el.get_attribute("type") or ""

            raw_name = (
                el.get_attribute("data-testid")
                or el.get_attribute("data-cy")
                or el.get_attribute("name")
                or el.get_attribute("id")
                or el.get_attribute("aria-label")
                or el.get_attribute("placeholder")
                or el.get_attribute("title")
                or f"element{i}"
            )

            if not raw_name.strip() and tag == "input":
                label = driver.execute_script("""
                    const input = arguments[0];
                    const labels = document.querySelectorAll("label");
                    for (const l of labels) {
                        if (l.htmlFor === input.id) return l.innerText;
                    }
                    return "";
                """, el)
                raw_name = label or f"element{i}"

            print("🧪 DEBUG: ATTRIBUTES ->",
                "id:", el.get_attribute("id"),
                "| name:", el.get_attribute("name"),
                "| data-testid:", el.get_attribute("data-testid"),
                "| placeholder:", el.get_attribute("placeholder"))

            safe_name = sanitize_name(raw_name)
            while safe_name in seen_names:
                safe_name += f"_{i}"
            seen_names.add(safe_name)

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

            id_attr = driver.execute_script("return arguments[0].id;", el)
            name_attr = driver.execute_script("return arguments[0].name;", el)
            class_attr = el.get_attribute("class")

            if id_attr:
                by = "id"
                selector = id_attr
            elif name_attr:
                by = "name"
                selector = name_attr
            elif class_attr and len(class_attr.split()) == 1:
                by = "css"
                selector = f".{class_attr.strip()}"
            else:
                by = "xpath"
                selector = xpath

            if tag == "textarea":
                action = "enterText"
                sample_text = "sample input"
                element_type = "textarea"
            elif tag == "input":
                if input_type == "checkbox":
                    action = "click"
                    sample_text = ""
                    element_type = "checkbox"
                elif input_type == "radio":
                    action = "click"
                    sample_text = ""
                    element_type = "radiobutton"
                elif input_type in ["submit", "button"]:
                    action = "click"
                    sample_text = ""
                    element_type = "button"
                else:
                    action = "enterText"
                    sample_text = "sample input"
                    element_type = "textbox"
            elif tag == "select":
                action = "select"
                sample_text = ""
                element_type = "dropdown"
            elif tag in ["button", "a", "div"] and (el.get_attribute("role") == "button" or tag == "button"):
                action = "click"
                sample_text = ""
                element_type = "button"
            else:
                action = "click"
                sample_text = ""
                element_type = "button"

            validations.append({
                "name": safe_name,
                "by": by,
                "selector": selector,
                "action": action,
                "sampleText": sample_text,
                "type": element_type,
                "label": raw_name.strip()
            })

            print(f"✅ {safe_name}: by={by}, selector={selector}")

        except Exception as e:
            print(f"⚠️ Error scraping element[{i}]: {e}")
            continue

    driver.quit()
    return validations


def sanitize_name(name):
    name = re.sub(r"[^\w]", "_", name)
    if not name or not name[0].isalpha():
        name = f"field_{name}"
    return name.lower()



def suggest_validations(url):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(30)  # ⏳ give time for JS to hydrate
    WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.XPATH, "//body"))
    )


    #raw_elements = driver.find_elements(By.XPATH, """//input | //textarea | //select | //button | //*[@role='button'] | //a[@href]""")
    #raw_elements = driver.find_elements(By.XPATH, """//*[contains(@id, 'email') or contains(@name, 'email')]""")
    raw_elements = driver.find_elements(By.XPATH, """//input | //textarea | //select | //button | //*[@role='button'] | //a[@href] | //div[@role='button']""")

    validations = []
    seen_names = set()

    for i, el in enumerate(raw_elements):
        try:
            print("🧩 HTML:", el.get_attribute("outerHTML"))

            if not el.is_displayed() or not el.is_enabled():
                continue

            tag = el.tag_name
            input_type = el.get_attribute("type") or ""

            # Get raw label for naming (variable name) and selector separately
            raw_name = (
                el.get_attribute("data-testid")
                or el.get_attribute("data-cy")
                or el.get_attribute("name")
                or el.get_attribute("id")
                or el.get_attribute("aria-label")
                or el.get_attribute("placeholder")
                or el.get_attribute("title")
                or f"element{i}"
            )
            if not raw_name.strip() and tag == "input":
                label = driver.execute_script("""
                    const input = arguments[0];
                    const labels = document.querySelectorAll("label");
                    for (const l of labels) {
                        if (l.htmlFor === input.id) return l.innerText;
                    }
                    return "";
                """, el)
                raw_name = label or f"element{i}"

            print("🧪 DEBUG: ATTRIBUTES ->",
                "id:", el.get_attribute("id"),
                "| name:", el.get_attribute("name"),
                "| data-testid:", el.get_attribute("data-testid"),
                "| placeholder:", el.get_attribute("placeholder"))
            safe_name = sanitize_name(raw_name)
            while safe_name in seen_names:
                safe_name += f"_{i}"
            seen_names.add(safe_name)

            # Generate fallback XPath
            xpath = driver.execute_script("""
                function absoluteXPath(element) {
                    const idx = (sib, name) => sib
                      ? idx(sib.previousElementSibling, name || sib.localName) + (sib.localName == name)
                      : 1;
                    const segs = elm => !elm || elm.nodeType !== 1
                      ? ['']
                      : elm.id && document.getElementById(elm.id) === elm
                      ? [`id("${elm.id}")`]
                      : [...segs(elm.parentNode), `${elm.localName.toLowerCase()}[${idx(elm)}]`];
                    return segs(element).join('/');
                }
                return absoluteXPath(arguments[0]);
            """, el)

            # Determine locator strategy
            id_attr = driver.execute_script("return arguments[0].id;", el)
            name_attr = driver.execute_script("return arguments[0].name;", el)

            class_attr = el.get_attribute("class")

            if id_attr:
                by = "id"
                selector = id_attr
            elif name_attr:
                by = "name"
                selector = name_attr
            elif class_attr and len(class_attr.split()) == 1:
                by = "css"
                selector = f".{class_attr.strip()}"
            else:
                by = "xpath"
                selector = xpath

            # Determine type of element
            if tag == "textarea":
                action = "enterText"
                sample_text = "sample input"
                element_type = "textarea"
            elif tag == "input":
                if input_type == "checkbox":
                    action = "click"
                    sample_text = ""
                    element_type = "checkbox"
                elif input_type == "radio":
                    action = "click"
                    sample_text = ""
                    element_type = "radiobutton"
                elif input_type in ["submit", "button"]:
                    action = "click"
                    sample_text = ""
                    element_type = "button"
                else:
                    action = "enterText"
                    sample_text = "sample input"
                    element_type = "textbox"
            elif tag == "select":
                action = "select"
                sample_text = ""
                element_type = "dropdown"
            elif tag in ["button", "a", "div"] and (el.get_attribute("role") == "button" or tag == "button"):
                action = "click"
                sample_text = ""
                element_type = "button"
            else:
                action = "click"
                sample_text = ""
                element_type = "button"

            validations.append({
                "name": safe_name,         # Java-safe field name (e.g., field_1_email)
                "by": by,                  # id | name | css | xpath
                "selector": selector,      # original "1-email" or raw value
                "action": action,
                "sampleText": sample_text,
                "type": element_type,
                "label": raw_name.strip()  # optional human label
            })

            print(f"✅ {safe_name}: by={by}, selector={selector}")

        except Exception as e:
            print(f"⚠️ Failed to process element[{i}]: {e}")
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
    time.sleep(30)  # ⏳ give time for JS to hydrate
    WebDriverWait(driver, 30).until(
    EC.presence_of_all_elements_located((By.XPATH, "//body"))
    )


    try:
        wait = WebDriverWait(driver, 10)

        user_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@type='email' or contains(@name, 'user') or contains(@id, 'user')]")
        ))
        pass_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@type='password']")
        ))
        login_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Login') or @type='submit']")
        ))

        user_input.clear()
        user_input.send_keys(username)
        pass_input.clear()
        pass_input.send_keys(password)
        login_btn.click()
        time.sleep(3)

    except Exception as e:
        print(f"⚠️ Login failed or not needed: {e}")

    print(f"🔄 Scraping post-login page: {driver.current_url}")

    #raw_elements = driver.find_elements(By.XPATH, """//input | //textarea | //select | //button | //*[@role='button'] | //a[@href]""")
    #raw_elements = driver.find_elements(By.XPATH, """//*[contains(@id, 'email') or contains(@name, 'email')]""")
    raw_elements = driver.find_elements(By.XPATH, """//input | //textarea | //select | //button | //*[@role='button'] | //a[@href] | //div[@role='button']""")

    validations = []
    seen_names = set()

    for i, el in enumerate(raw_elements):
        try:
            print("🧩 HTML:", el.get_attribute("outerHTML"))

            if not el.is_displayed() or not el.is_enabled():
                continue

            tag = el.tag_name
            input_type = el.get_attribute("type") or ""

            raw_name = (
                el.get_attribute("data-testid")
                or el.get_attribute("data-cy")
                or el.get_attribute("name")
                or el.get_attribute("id")
                or el.get_attribute("aria-label")
                or el.get_attribute("placeholder")
                or el.get_attribute("title")
                or f"element{i}"
            )

            if not raw_name.strip() and tag == "input":
                label = driver.execute_script("""
                    const input = arguments[0];
                    const labels = document.querySelectorAll("label");
                    for (const l of labels) {
                        if (l.htmlFor === input.id) return l.innerText;
                    }
                    return "";
                """, el)
                raw_name = label or f"element{i}"


            print("🧪 DEBUG: ATTRIBUTES ->",
                "id:", el.get_attribute("id"),
                "| name:", el.get_attribute("name"),
                "| data-testid:", el.get_attribute("data-testid"),
                "| placeholder:", el.get_attribute("placeholder"))


            safe_name = sanitize_name(raw_name)
            while safe_name in seen_names:
                safe_name += f"_{i}"
            seen_names.add(safe_name)

            xpath = driver.execute_script("""
                function absoluteXPath(element) {
                    const idx = (sib, name) => sib
                      ? idx(sib.previousElementSibling, name || sib.localName) + (sib.localName == name)
                      : 1;
                    const segs = elm => !elm || elm.nodeType !== 1
                      ? ['']
                      : elm.id && document.getElementById(elm.id) === elm
                      ? [`id("${elm.id}")`]
                      : [...segs(elm.parentNode), `${elm.localName.toLowerCase()}[${idx(elm)}]`];
                    return segs(element).join('/');
                }
                return absoluteXPath(arguments[0]);
            """, el)

            id_attr = driver.execute_script("return arguments[0].id;", el)
            name_attr = driver.execute_script("return arguments[0].name;", el)

            class_attr = el.get_attribute("class")

            if id_attr:
                by = "id"
                selector = id_attr
            elif name_attr:
                by = "name"
                selector = name_attr
            elif class_attr and len(class_attr.split()) == 1:
                by = "css"
                selector = f".{class_attr.strip()}"
            else:
                by = "xpath"
                selector = xpath

            if tag == "textarea":
                action = "enterText"
                sample_text = "sample input"
                element_type = "textarea"
            elif tag == "input":
                if input_type == "checkbox":
                    action = "click"
                    sample_text = ""
                    element_type = "checkbox"
                elif input_type == "radio":
                    action = "click"
                    sample_text = ""
                    element_type = "radiobutton"
                elif input_type in ["submit", "button"]:
                    action = "click"
                    sample_text = ""
                    element_type = "button"
                else:
                    action = "enterText"
                    sample_text = "sample input"
                    element_type = "textbox"
            elif tag == "select":
                action = "select"
                sample_text = ""
                element_type = "dropdown"
            elif tag in ["button", "a", "div"] and (el.get_attribute("role") == "button" or tag == "button"):
                action = "click"
                sample_text = ""
                element_type = "button"
            else:
                action = "click"
                sample_text = ""
                element_type = "button"

            validations.append({
                "name": safe_name,
                "by": by,
                "selector": selector,
                "action": action,
                "sampleText": sample_text,
                "type": element_type,
                "label": raw_name.strip()
            })

            print(f"✅ {safe_name}: by={by}, selector={selector}")

        except Exception as e:
            print(f"⚠️ Error scraping element[{i}]: {e}")
            continue

    driver.quit()
    return validations

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "--save-cookies":
        target_url = sys.argv[2] if len(sys.argv) >= 3 else "https://my.charitableimpact.com/login"
        save_cookies_after_manual_login(target_url)
    elif sys.argv[1] == "--scrape":
        target_url = sys.argv[2]
        validations = suggest_validations_with_bypass(target_url)
        print(f"🎯 Total elements extracted: {len(validations)}")


#To handle cloudflare issue name="cf-turnstile-response we need to do the following to bypass the login page and scrape the DOM for validations
#This will allow the program to bypass the login page and scrape the DOM for validations
#This program should be run once to store the cookies for the site Command to run python dom_scraper.py --save-cookies https://my.charitableimpact.com/login
#If you also want to allow scraping via CLI:then run the command python dom_scraper.py --scrape https://my.charitableimpact.com/groups

#This will allow the program to bypass the login page and scrape the DOM for validations
#After running this, you can call suggest_validations_authenticated with the URL and your credentials to scrape the DOM
#Example: suggest_validations_authenticated("https://my.charitableimpact.com/some-page", "your_username", "your_password")
#This will return a list of validations that can be used to generate the Java code for the page object model
#Make sure to have the required packages installed:
#pip install undetected-chromedriver selenium