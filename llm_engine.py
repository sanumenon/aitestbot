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
# Load restriction prompt from external file
RESTRICTION_PROMPT_PATH = "RESTRICTION_PROMPT.txt"
if not os.path.exists(RESTRICTION_PROMPT_PATH):
    raise FileNotFoundError(f"❌ Restriction prompt file not found: {RESTRICTION_PROMPT_PATH}")

with open(RESTRICTION_PROMPT_PATH, "r", encoding="utf-8") as file:
    RESTRICTION_PROMPT = file.read().strip()

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
    #if not any(RESTRICTION_PROMPT.strip() in m["content"] for m in prompt_messages if m["role"] == "system"):
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