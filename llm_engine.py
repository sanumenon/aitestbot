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
# def initialize_local_model_old():
#     global local_tokenizer, local_model, local_chatbot_pipeline
#     try:
#         #model_id = st.session_state.get("local_model_name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
#         #model_id = st.session_state.get("local_model_name", "mistralai/Mistral-7B-Instruct-v0.2")
#         #model_id = st.session_state.get("local_model_name", "teknium/OpenHermes-2.5-Mistral-7B")
#         model_id = st.session_state.get("local_model_name", "google/gemma-2b")
#         print(f"🧠 Loading local model: {model_id}")

#         local_tokenizer = AutoTokenizer.from_pretrained(model_id)

#         # ✅ Fix: disable meta tensors and allow CPU-based loading
#         local_model = AutoModelForCausalLM.from_pretrained(
#         model_id,
#         torch_dtype=torch.float32,
#         low_cpu_mem_usage=True,
#         device_map={"": "cpu"}  # ✅ Force CPU load safely
#     )


#         local_chatbot_pipeline = pipeline(
#             "text-generation",
#             model=local_model,
#             tokenizer=local_tokenizer,
#             max_new_tokens=512,
#             do_sample=True,
#             temperature=0.7,
#             top_p=0.95
#         )

#         print("✅ Local model loaded successfully.")
#         return True

#     except Exception as e:
#         print(f"❌ Failed to load local model: {e}")
#         return False
    
def initialize_local_model(model_name):
    if not model_name or model_name.strip() == "":
        print(f"🚫 Empty model name received in initialize_local_model.")
        return False
        # Get the current date and time
    current_datetime = datetime.now()
    print(f"Model name received in initialize_local_model.{model_name}")

    # Extract and format the time
    current_time = current_datetime.strftime("%H:%M:%S")
    print(f"🔁 initialize_local_model called at {current_time}")

    global local_tokenizer, local_model, local_chatbot_pipeline

    try:
        model_id = st.session_state.get("last_loaded_model") or model_name
        print(f"🧠 Loading local model: {model_id}")
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # Correctly assign to global variables
        local_tokenizer = AutoTokenizer.from_pretrained(model_id)
        local_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto"
        )

        if not getattr(local_tokenizer, "chat_template", None):
            print("⚠️ Tokenizer does not have a chat_template")

        local_chatbot_pipeline = pipeline(
            "text-generation",
            model=local_model,
            tokenizer=local_tokenizer,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            pad_token_id=local_tokenizer.eos_token_id
        )
        current_datetime = datetime.now()
        current_time = current_datetime.strftime("%H:%M:%S")
        print(f"✅ Local model loaded successfully. {current_time} ")
        return True

    except Exception as e:
        print(f"❌ Failed to load local model: {e}")
        return False





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


def chat_with_llm(prompt_messages: list, temperature=0.7) -> tuple[str, float]:
    start_time = time.time()
    print(f"🔍 chat_with_llm called with mode: {llm_mode}")

    restriction_prompt = (
        "You are a highly specialized AI test case generator for the application my.charitableimpact.com.\n"
        "You must only respond to test case generation requests strictly related to the domain charitableimpact.com.\n"
        "\n"
        "Only generate test automation code in **Java** using **Selenium 4.2 or higher**, **TestNG**, and **Maven**, following the **Page Object Model (POM)** design pattern.\n"
        "- Use **WebDriverManager** for browser driver management (no hardcoded paths like `C:/.../chromedriver.exe`).\n"
        "- Do not reference Selenium IDE or any other language/framework.\n"
        "\n"
        "For complex prompts that include **multiple user actions** (e.g., login, navigate to group, edit settings, save, verify):\n"
        "✔️ Break down the prompt into logical user flows or functional modules.\n"
        "✔️ Generate a **separate Page class and a corresponding Test class** for each flow/module.\n"
        "✔️ Ensure that the generated Test classes **preserve user navigation flow**, e.g., login before editing, or search before selecting a charity.\n"
        "✔️ If required, chain flows together in the Test method while using distinct Page classes.\n"
        "✔️ Use only elements present on my.charitableimpact.com, and follow real-world flows.\n"
        "\n"
        "If the prompt is off-topic (not about charitableimpact.com), respond with:\n"
        "'❌ I can only help with test case generation for the domain charitableimpact.com using Java + Selenium + TestNG + Maven.'\n"
        "\n"
        "Valid environments include:\n"
        "- https://my.charitableimpact.com (Production)\n"
        "- https://qa.my.charitableimpact.com (QA)\n"
        "- https://stage.my.charitableimpact.com (Stage)\n"
        "\n"
        "Common valid paths include (but are not limited to):\n"
        "- `/users/login`, `/dashboard`, `/groups/edit`, `/impact-account/...`, `/search?...`, `/give/...`, `/charities/...`, `/user/...`, `/campaigns/...`\n"
        "\n"
        "**Ensure that the generated code is complete, follows best practices, compiles without error, and supports full test execution using Maven.**\n"
    )

    if not any(m.get("role") == "system" and "You are a highly specialized AI" in m.get("content", "") for m in prompt_messages):
        prompt_messages.insert(0, {"role": "system", "content": restriction_prompt})

    final_response = "❌ No response generated."
    
    if llm_mode == "local" and local_model:
        try:
            # Check if model supports chat template
            if hasattr(local_tokenizer, "chat_template") and local_tokenizer.chat_template:
                formatted_input = local_tokenizer.apply_chat_template(
                    prompt_messages, tokenize=False, add_generation_prompt=True
                )
            else:
                # fallback: concatenate restriction and user prompt for base models
                formatted_input = restriction_prompt + "\n\nUser: " + prompt_messages[-1]["content"]

            response = local_chatbot_pipeline(
                formatted_input,
                max_new_tokens=512,
                do_sample=True,
                temperature=temperature,
                pad_token_id=local_tokenizer.eos_token_id
            )[0]["generated_text"]

            final_response = response.replace(formatted_input, "").strip()

        except Exception as e:
            final_response = f"❌ Local model inference failed: {str(e)}"

    elif llm_mode == "openai" and openai_client:
        try:
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL_NAME,
                messages=prompt_messages,
                temperature=temperature,
            )
            final_response = response.choices[0].message.content.strip()
        except Exception as e:
            final_response = f"❌ OpenAI call failed: {str(e)}"

    else:
        final_response = "❌ Selected LLM mode is not available or failed to initialize."

    elapsed_time = round(time.time() - start_time, 2)
    return final_response, elapsed_time




# def chat_with_llm_old(prompt_messages: list, temperature=0.7) -> tuple[str, float]:
#     start_time = time.time()
#     # Debug logging
#     print(f"🔍 chat_with_llm called with mode: {llm_mode}")

#     # Inject restriction prompt only if not already present
#     restriction_prompt = (
#     "You are a highly specialized AI test case generator for the application my.charitableimpact.com.\n"
#     "You must only respond to test case generation requests strictly related to the domain charitableimpact.com.\n"
#     "\n"
#     "Only generate test automation code in **Java** using **Selenium 4.2 or higher**, **TestNG**, and **Maven**, following the **Page Object Model (POM)** design pattern.\n"
#     "- Use **WebDriverManager** for browser driver management (no hardcoded paths like `C:/.../chromedriver.exe`).\n"
#     "- Do not reference Selenium IDE or any other language/framework.\n"
#     "\n"
#     "For complex prompts that include **multiple user actions** (e.g., login, navigate to group, edit settings, save, verify):\n"
#     "✔️ Break down the prompt into logical user flows or functional modules.\n"
#     "✔️ Generate a **separate Page class and a corresponding Test class** for each flow/module.\n"
#     "✔️ Ensure that the generated Test classes **preserve user navigation flow**, e.g., login before editing, or search before selecting a charity.\n"
#     "✔️ If required, chain flows together in the Test method while using distinct Page classes.\n"
#     "✔️ Use only elements present on my.charitableimpact.com, and follow real-world flows.\n"
#     "\n"
#     "If the prompt is off-topic (not about charitableimpact.com), respond with:\n"
#     "'❌ I can only help with test case generation for the domain charitableimpact.com using Java + Selenium + TestNG + Maven.'\n"
#     "\n"
#     "Valid environments include:\n"
#     "- https://my.charitableimpact.com (Production)\n"
#     "- https://qa.my.charitableimpact.com (QA)\n"
#     "- https://stage.my.charitableimpact.com (Stage)\n"
#     "\n"
#     "Common valid paths include (but are not limited to):\n"
#     "- `/users/login`, `/dashboard`, `/groups/edit`, `/impact-account/...`, `/search?...`, `/give/...`, `/charities/...`, `/user/...`, `/campaigns/...`\n"
#     "\n"
#     "**Ensure that the generated code is complete, follows best practices, compiles without error, and supports full test execution using Maven.**\n"
#     )
#     if not any(m.get("role") == "system" and "You are a highly specialized AI" in m.get("content", "") for m in prompt_messages):
#         prompt_messages.insert(0, {"role": "system", "content": restriction_prompt})

#     # Process based on LLM mode
#     if llm_mode == "local" and local_model:
#         try:
#             formatted_input = local_tokenizer.apply_chat_template(
#                 prompt_messages, tokenize=False, add_generation_prompt=True
#             )
#             response = local_chatbot_pipeline(
#                 formatted_input,
#                 max_new_tokens=512,
#                 do_sample=True,
#                 temperature=temperature,
#                 pad_token_id=local_tokenizer.eos_token_id
#             )[0]["generated_text"]
#             final_response = response.replace(formatted_input, "").strip()
#         except Exception as e:
#             final_response = f"❌ Local model inference failed: {str(e)}"

#     elif llm_mode == "openai" and openai_client:
#         try:
#             response = openai_client.chat.completions.create(
#                 model=OPENAI_MODEL_NAME,
#                 messages=prompt_messages,
#                 temperature=temperature,
#             )
#             final_response = response.choices[0].message.content.strip()
#         except Exception as e:
#             final_response = f"❌ OpenAI call failed: {str(e)}"

#     else:
#         final_response = "❌ Selected LLM mode is not available or failed to initialize."

#     end_time = time.time()
#     elapsed_time = round(end_time - start_time, 2)

#     return final_response, elapsed_time




# Use RAG-enhanced chat for test case generation
def simple_chat_prompt(user_prompt: str) -> str:
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
