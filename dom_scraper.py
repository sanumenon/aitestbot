# dom_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def suggest_validations(url):
    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.get(url)

    def get_elements(xpath):
        return driver.find_elements(By.XPATH, xpath)

    # Primary XPath: standard interactable elements
    primary_xpath = "//input | //button | //textarea | //select"
    elements = get_elements(primary_xpath)

    # Fallback: if fewer than 3 elements, include links, roles, and all id-bearing elements
    if len(elements) < 3:
        fallback_xpath = f"{primary_xpath} | //a | //div[@role='button'] | //*[@id]"
        elements = get_elements(fallback_xpath)

    validations = []
    for i, el in enumerate(elements[:10]):  # Limit max elements for speed
        try:
            tag = el.tag_name
            name_attr = el.get_attribute("name") or f"element{i}"
            id_attr = el.get_attribute("id")
            type_attr = el.get_attribute("type")

            # Absolute XPath via JavaScript
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

            # Decide action type
            if tag in ["input", "textarea"]:
                action = "enterText"
                sample_text = "sample input"
            elif tag in ["button", "select", "a", "div"]:
                action = "click"
                sample_text = ""
            else:
                action = "click"
                sample_text = ""

            validations.append({
                "name": name_attr.replace(" ", "_"),
                "xpath": f"//*[@id='{id_attr}']" if id_attr else xpath,
                "action": action,
                "sampleText": sample_text
            })

        except Exception as e:
            continue

    driver.quit()
    return validations
