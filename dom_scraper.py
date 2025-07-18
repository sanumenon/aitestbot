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
from selenium.common.exceptions import TimeoutException

COOKIE_FILE = "cookies.pkl"

def format_dom_compact(dom_elements):
    """Return compact LLM-friendly DOM as text block"""
    if not dom_elements:
        return ""
    return "\n".join(to_compact_findby_line(el) for el in dom_elements)


def to_compact_findby_line(el):
    """Compact DOM line: field_name | by=selector"""
    by = el.get("by", "").strip()
    selector = el.get("selector", "").strip()
    name = el.get("name", "").strip()
    return f"{name} | {by}={selector}"


def sanitize_name(name):
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if not name or not name[0].isalpha():
        name = f"field_{name}"
    return name.lower()

def save_cookies_after_manual_login(url):
    print("🚀 Launching browser for manual login...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=137)

    driver.get(url)
    input("🔐 Complete login and press ENTER to save cookies...")
    with open(COOKIE_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
        print(f"✅ Cookies saved to {COOKIE_FILE}")
    driver.quit()

def load_browser_with_cookies(url):
    print("🚀 Launching browser with saved cookies...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=137)
    driver.get(url)
    time.sleep(2)

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

    driver.get(url)
    return driver

def wait_for_js_hydration(driver, timeout=20):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, '//input'))
        )
        WebDriverWait(driver, timeout).until(
            lambda d: any(el.get_attribute("id") for el in d.find_elements(By.XPATH, '//input'))
        )
    except Exception as e:
        print(f"⚠️ Timeout or hydration issue: {e}")

def extract_element_metadata(driver, element):
    def get_label(el):
        label = driver.execute_script('''
            const input = arguments[0];
            const labels = document.querySelectorAll("label");
            for (const l of labels) {
                if (l.htmlFor === input.id) return l.innerText;
            }
            return "";
        ''', el)
        return label or el.get_attribute("placeholder") or el.get_attribute("aria-label") or ""

    tag = element.tag_name
    input_type = element.get_attribute("type") or ""

    raw_name = (
        element.get_attribute("data-testid")
        or element.get_attribute("data-cy")
        or element.get_attribute("name")
        or element.get_attribute("id")
        or element.get_attribute("placeholder")
        or element.get_attribute("aria-label")
        or get_label(element)
        or "unknown"
    )

    safe_name = sanitize_name(raw_name)
    print(f"🧪 Raw name used: {raw_name}")

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
    else:
        action = "click"
        sample_text = ""
        element_type = "button"

    id_attr = element.get_attribute("id")
    name_attr = element.get_attribute("name")
    class_attr = element.get_attribute("class")

    by, selector = None, None

    if id_attr:
        matches = driver.find_elements(By.ID, id_attr)
        if len(matches) == 1:
            by = "id"
            selector = id_attr

    if not selector and class_attr and len(class_attr.split()) == 1:
        matches = driver.find_elements(By.CSS_SELECTOR, f".{class_attr.strip()}")
        if len(matches) == 1:
            by = "css"
            selector = f".{class_attr.strip()}"

    if not selector and name_attr:
        matches = driver.find_elements(By.NAME, name_attr)
        if len(matches) == 1:
            by = "name"
            selector = name_attr

    if not selector:
        by = "xpath"
        selector = driver.execute_script('''
            function absoluteXPath(element) {
                const idx = (sib, name) => sib
                    ? idx(sib.previousElementSibling, name || sib.localName) + (sib.localName == name)
                    : 1;
                const segs = elm => !elm || elm.nodeType !== 1
                    ? ['']
                    : elm.id && document.getElementById(elm.id) === elm
                    ? [`id("${elm.id}")`]
                    : [...segs(elm.parentNode), `${elm.localName.toLowerCase()}[${idx(elm)}]`];
                return segs(element).join('/')
            }
            return absoluteXPath(arguments[0]);
        ''', element)

    return {
        "name": safe_name,
        "by": by,
        "selector": selector,
        "action": action,
        "sampleText": sample_text,
        "type": element_type,
        "label": raw_name.strip(),
    }

def scrape_input_fields_after_login(driver):
    wait_for_js_hydration(driver)
    print("\n🔍 Extracting input fields...")
    input_elements = driver.find_elements(By.XPATH, "//input | //textarea | //select | //button | //*[@role='button'] | //a[@href] | //div[@role='button']")
    results = []
    seen_names = set()
    for idx, el in enumerate(input_elements):
        if not el.is_displayed() or not el.is_enabled():
            continue
        meta = extract_element_metadata(driver, el)
        if meta["name"] in seen_names:
            meta["name"] += f"_{idx}"
        seen_names.add(meta["name"])
        print(f"✅ {meta['name']}: by={meta['by']}, selector={meta['selector']}")

        results.append(meta)
    return results

def suggest_validations_authenticated(url, username, password,return_driver=False):
    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    results = []

    try:
        wait = WebDriverWait(driver, 20)

        # 🚨 Point 2: Warn if URL doesn't look like a login page
        if "login" not in url.lower():
            raise Exception("⚠️ The provided URL doesn't appear to be a login page. Please provide the direct login URL.")

        # ✅ Check if email input exists
        try:
            email_input = wait.until(EC.presence_of_element_located((
                By.XPATH,
                "//input[contains(@id,'email') or contains(@name,'email') or contains(@placeholder,'email') or @type='email']"
            )))
        except TimeoutException:
            raise Exception("❌ Email input field not found. Login form may be missing or page structure has changed.")

        email_input.clear()
        email_input.send_keys(username)

        # ✅ Check if password input exists
        try:
            password_input = wait.until(EC.presence_of_element_located((
                By.XPATH,
                "//input[contains(@id,'password') or contains(@name,'password') or contains(@placeholder,'password') or @type='password']"
            )))
        except TimeoutException:
            raise Exception("❌ Password input field not found. Login form may be incomplete.")

        password_input.clear()
        password_input.send_keys(password)

        # ✅ Attempt to click login
        try:
            login_button = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(translate(text(),'LOGIN','login'),'login') or @type='submit']"
            )))
        except TimeoutException:
            raise Exception("❌ Login button not found or not clickable.")

        login_button.click()

        # ✅ Wait for post-login confirmation (either dashboard or logout text)
        wait.until(lambda d: "dashboard" in d.current_url.lower() or
                            any(e.is_displayed() for e in d.find_elements(By.XPATH, "//*[contains(text(),'Logout') or contains(text(),'My Account')]")))

        print("✅ Login successful. Extracting DOM fields.")
        results = scrape_input_fields_after_login(driver)

    except Exception as e:
        print(f"⚠️ Login failed: {e}")
    finally:
        if return_driver:
            return results, driver
        else:
            driver.quit()
            return results




def suggest_validations_with_bypass(url):
    driver = load_browser_with_cookies(url)
    wait_for_js_hydration(driver)
    print(f"🔄 Scraping hydrated page: {driver.current_url}")
    results = scrape_input_fields_after_login(driver)
    driver.quit()
    return results

def suggest_validations_smart(url, username=None, password=None, use_cookies=False):
    print(f"🧭 suggest_validations_smart: URL={url}, user={username}, cookie_mode={use_cookies}")
    
    if use_cookies:
        return suggest_validations_with_bypass(url)
    elif username and password:
        return suggest_validations_authenticated(url, username, password)
    else:
        return suggest_validations(url)

def suggest_validations(url=None, driver=None):
    new_driver = False
    if driver is None:
        options = Options()
        options.add_argument("--headless=new")
        driver = webdriver.Chrome(options=options)
        new_driver = True

    if url:
        driver.get(url)

    wait_for_js_hydration(driver)
    results = scrape_input_fields_after_login(driver)

    if new_driver:
        driver.quit()

    return results




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