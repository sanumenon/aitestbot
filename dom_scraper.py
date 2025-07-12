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
    driver.get("https://charitableimpact.com")
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


def suggest_validations_authenticated(url, username, password):
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(30)
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
        time.sleep(5)

        print(f"🔐 Logged in. Scraping inputs from: {driver.current_url}")
        results = scrape_input_fields_after_login(driver)

    except Exception as e:
        print(f"⚠️ Login failed or scraping error: {e}")
        results = []

    driver.quit()
    return results


def suggest_validations_with_bypass(url):
    driver = load_browser_with_cookies(url)
    wait_for_js_hydration(driver)
    print(f"🔄 Scraping hydrated page: {driver.current_url}")
    results = scrape_input_fields_after_login(driver)
    driver.quit()
    return results


def suggest_validations(url):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    wait_for_js_hydration(driver)
    results = scrape_input_fields_after_login(driver)
    driver.quit()
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "--save-cookies":
        target_url = sys.argv[2] if len(sys.argv) >= 3 else "https://my.charitableimpact.com/login"
        save_cookies_after_manual_login(target_url)
    elif sys.argv[1] == "--scrape":
        target_url = sys.argv[2]
        validations = suggest_validations_with_bypass(target_url)
        print(f"🎯 Total elements extracted: {len(validations)}")
    elif sys.argv[1] == "--scrape-input-fields":
        target_url = sys.argv[2]
        driver = load_browser_with_cookies(target_url)
        scrape_input_fields_after_login(driver)
        driver.quit()



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