# llm_engine.py
import os
import openai
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from rag_search import retrieve_context
import torch
import warnings
import streamlit as st
import time
from datetime import datetime

warnings.filterwarnings("ignore")

load_dotenv()

os.environ["USER_AGENT"] = "CharitableImpact-TestGenBot/1.0"
# Load OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = "gpt-3.5-turbo"

# Global state
RESTRICTION_PROMPT = """
    You are a highly specialized AI test case generator for the application my.charitableimpact.com.
    Only respond to test case generation requests that are clearly related to charitableimpact.com or any of its valid subdomains, including my.charitableimpact.com, my.qa.charitableimpact.com, and my.stg.charitableimpact.com.

     **Code Requirements:**
    - Only generate test automation code in **Java** using **Selenium 4.2 or higher**, **TestNG**, and **Maven**.
    - Follow the **Page Object Model (POM)** design pattern.
    - Use **WebDriverManager** for driver setup ( No hardcoded paths like `C:/.../chromedriver.exe`).
    -  Always include `import io.github.bonigarcia.wdm.WebDriverManager;` in the Test class.
    - Use Selenium 4+ syntax for waits, e.g., `new WebDriverWait(driver, Duration.ofSeconds(10))`, and always import `java.time.Duration`.
    -  Do not use deprecated timeout APIs like `TimeUnit.SECONDS` or `implicitlyWait(10, TimeUnit.SECONDS)`.
    -  Always use `Duration.ofSeconds(10)` for waits and timeouts, and import `java.time.Duration`.
    - Assume latest stable **Selenium 4.2+**, **TestNG**, and **Java 11+**.
    -  Never use deprecated methods like `findElementBy...`.
    -  Never reference Selenium IDE or other languages/frameworks.

     All test classes must include ExtentReports and WebDriverManager:
    -  Always import the following in every Test class:
     Do NOT call ExtentReportManager.getExtent() — that method is not allowed
    ```java
    import com.aventstack.extentreports.ExtentReports;
    import com.aventstack.extentreports.ExtentTest;
    import com.aventstack.extentreports.Status;
    import com.charitableimpact.config.ExtentReportManager;
    import io.github.bonigarcia.wdm.WebDriverManager;
    ```
    -  At the beginning of each test method, initialize logging:
    ```java
    ExtentTest test = ExtentReportManager.createTest(TestName);
    ```
    -  Log steps using:
    ```java
    test.log(Status.INFO, Step description here);
    ```
    -  In `@AfterClass`, call:
    ```java
    ExtentReportManager.flush();
    ```
    -  Reports must be saved to: `generated_code/ExtentReport/ExtentReport.html`
    -  Do NOT skip any of the above steps. Assume all required classes and configs are available.
     **POM Structure Enforcement:**
     Always generate **two separate classes** per module:
      1. A **Page Object class** (e.g., `LoginPage.java`) with `@FindBy`-annotated WebElements and methods for user actions.
      2. A **Test class** (e.g., `LoginTest.java`) with WebDriver setup/teardown using `@BeforeClass/@AfterClass` and `@Test`-annotated methods.
     In Page class constructor, always initialize elements using `PageFactory.initElements(driver, this);`.
     Page classes must **not contain any WebDriver setup** or TestNG annotations.
     Test classes must **only use methods from their Page class** to perform actions.
     Classes must be **self-contained**, Maven-compatible, and **compile without errors**.
     Always include **all required `import` statements** explicitly.
     **User Flow Decomposition:**
     If the prompt contains multiple actions (e.g., login → edit → verify), break it into logical flows.
     Generate a **Page class and corresponding Test class** for each flow.
     Test classes may chain multiple Page classes but should follow actual navigation paths.
     **Restrictions:**
     Never combine multiple Java classes in the same code block.
     Never generate incomplete or partial class bodies.
     Never skip class or method closing braces.
     Do not use elements or flows that don't exist on charitableimpact.com.
     **Output Format (Strict):**
    - Start each class with a clear header **at the beginning of the line**.
    - Use this format exactly:
    === PAGE OBJECT CLASS: <ClassName> ===
    ```java
    // full page class code here
    ```
    === TEST CLASS: <ClassName> ===
    ```java
    // full test class code here
    ```
    **Valid Environments:**
    - https://my.charitableimpact.com (Production)
    - https://my.qa.charitableimpact.com (QA)
    - https://my.stg.charitableimpact.com (Stage)
     **Valid paths include (but not limited to):**
    - `/users/login`, `/dashboard`, `/groups/edit`, `/impact-account/...`, `/search?...`, `/give/...`, `/charities/...`, `/user/...`, `/campaigns/...`
    If the prompt is unrelated to my.charitableimpact.com, you may respond:
    "This use case seems unrelated to *.charitableimpact.com or the given valid environments. Could you confirm the flow or page involved?"
    If it is related, proceed with test case generation as instructed , follow all code requirements strictly and generate full Java + Selenium + TestNG test classes.
    """.strip()
local_tokenizer = None
local_model = None
local_chatbot_pipeline = None
openai_client = None
llm_mode = "local"

# Initialize local model and tokenizer
# This will be called at startup to preload the default local model
# and tokenizer to avoid delays during user interactions.
# It will also handle the case where the local model fails to load.
# If the local model fails, it will fall back to OpenAI mode if available.
def initialize_local_model(model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
    current_datetime = datetime.now()
    current_time = current_datetime.strftime("%H:%M:%S")
    print(f"🔁 initialize_local_model called at {current_time}")
    print(f"Model name received in initialize_local_model.{model_name}")
    global local_tokenizer, local_model, local_chatbot_pipeline
    try:
        #model_id = st.session_state.get("local_model_name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        #model_id = st.session_state.get("local_model_name", "mistralai/Mistral-7B-Instruct-v0.2")
        #model_id = st.session_state.get("local_model_name", "teknium/OpenHermes-2.5-Mistral-7B")
        model_id = st.session_state.get("local_model_name", model_name) # Use provided model_name or fallback to session state
        print(f"🧠 Loading local model: {model_id}")

        local_tokenizer = AutoTokenizer.from_pretrained(model_id)

        # ✅ Fix: disable meta tensors and allow CPU-based loading
        device = "cpu"
        torch_dtype = torch.float32
        local_model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        device_map={"": device}
        )


        local_chatbot_pipeline = pipeline(
            "text-generation",
            model=local_model,
            tokenizer=local_tokenizer,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.95
        )

        print("✅ Local model loaded successfully.")
        current_datetime = datetime.now()
        current_time = current_datetime.strftime("%H:%M:%S")
        print(f"✅ Local model loaded successfully. {current_time} ")
        return True

    except Exception as e:
        print(f"❌ Failed to load local model: {e}")
        return False
    
# Initialize OpenAI client
# This will be called when switching to OpenAI mode or at startup if OpenAI mode is selected.
# It will check if the API key is set and attempt to create the OpenAI client.
# If the API key is missing or initialization fails, it will print an error message.
# If successful, it will set the global openai_client variable.
# This allows the app to use OpenAI for chat completions.
# It will also handle the case where the OpenAI client fails to initialize.
# If the OpenAI client fails, it will set llm_mode to None.
# This will prevent further OpenAI calls until the client is successfully initialized again.
# If the OpenAI API key is not set, it will print an error message and return
def initialize_openai_client():
    global openai_client
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY is missing.")
        return False
    try:
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI client initialized.")
        return True
    except Exception as e:
        print(f"❌ OpenAI client initialization failed: {e}")
        return False


# Call once at startup to preload default local model
#initialize_local_model()use this only when you want to # set the default local model at startup, otherwise use set_llm_mode("local") to switch modes dynamically


def set_llm_mode(mode: str):
    global llm_mode
    if mode == "openai":
        if initialize_openai_client():
            llm_mode = "openai"
        else:
            llm_mode = None
    elif mode == "local":
        if initialize_local_model():
            llm_mode = "local"
        else:
            llm_mode = None
    else:
        llm_mode = None
    print(f"🔁 LLM mode set to: {llm_mode}")

# Function to handle chat interactions with the LLM
def chat_with_llm(prompt_messages: list, temperature=0.7, return_usage=False) -> tuple:
    start_time = time.time()
    print(f"🔍 chat_with_llm called with mode: {llm_mode}")

    # Inject restriction prompt only if not already present
    if not any(RESTRICTION_PROMPT.strip() in m["content"] for m in prompt_messages if m["role"] == "system"):
        prompt_messages = [{"role": "system", "content": RESTRICTION_PROMPT}] + [
            m for m in prompt_messages if m["role"] != "system"]

    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # Handle Local LLM
    if llm_mode == "local" and local_model and local_chatbot_pipeline:
        try:
            if hasattr(local_tokenizer, "chat_template") and local_tokenizer.chat_template:
                formatted_input = local_tokenizer.apply_chat_template(
                    prompt_messages, tokenize=False, add_generation_prompt=True
                )
            else:
                print("⚠️ chat_template not supported, falling back to raw prompt merge")
                formatted_input = (
                    prompt_messages[0]["content"] + "\n\nUser: " + prompt_messages[-1]["content"]
                )

            print("🧠 Sending input to local model:")
            print(formatted_input[:300])

            result = local_chatbot_pipeline(
                formatted_input,
                max_new_tokens=512,
                do_sample=True,
                temperature=temperature,
                pad_token_id=getattr(local_tokenizer, "pad_token_id", local_tokenizer.eos_token_id)
            )

            if not result or not result[0].get("generated_text"):
                raise ValueError("⚠️ Local model returned empty result")

            final_response = result[0]["generated_text"].replace(formatted_input, "").strip()
            print(f"🧠 Local response length: {len(final_response.split())} tokens (approx)")

            # Approximate usage (no official token count from local model)
            usage["prompt_tokens"] = len(formatted_input.split())
            usage["completion_tokens"] = len(final_response.split())
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

        except Exception as e:
            final_response = f"❌ Local model inference failed: {str(e)}"

    # Handle OpenAI LLM
    elif llm_mode == "openai" and openai_client:
        try:
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL_NAME,
                messages=prompt_messages,
                temperature=temperature,
            )

            final_response = response.choices[0].message.content.strip()

            if hasattr(response, "usage"):
                usage["prompt_tokens"] = response.usage.prompt_tokens
                usage["completion_tokens"] = response.usage.completion_tokens
                usage["total_tokens"] = response.usage.total_tokens
                print(f"📊 Tokens — Prompt: {usage['prompt_tokens']}, Completion: {usage['completion_tokens']}, Total: {usage['total_tokens']}")

        except Exception as e:
            final_response = f"❌ OpenAI call failed: {str(e)}"

    else:
        final_response = "❌ Selected LLM mode is not available or failed to initialize."

    elapsed_time = round(time.time() - start_time, 2)

    if return_usage:
        return final_response, elapsed_time, usage
    else:
        return final_response, elapsed_time




# Use RAG-enhanced chat for test case generation
def simple_chat_prompt(user_prompt: str) -> tuple[str, float]:
    context = retrieve_context(user_prompt)
    return chat_with_llm([
        {
            "role": "system",
            "content": (
                "You are a senior QA automation engineer skilled in Java 11+, Selenium 4+, and TestNG.\n"
                "Use this help documentation:\n"
                f"{context}\n\n"
                "Generate full Selenium test cases in Java using Page Object Model based on the user's request."
            )
        },
        {"role": "user", "content": user_prompt}
    ])