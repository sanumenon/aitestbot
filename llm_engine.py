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

warnings.filterwarnings("ignore")

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = "gpt-3.5-turbo"

# Global state
local_tokenizer = None
local_model = None
local_chatbot_pipeline = None
openai_client = None
llm_mode = "local"


def initialize_local_model():
    global local_tokenizer, local_model, local_chatbot_pipeline
    try:
        model_id = st.session_state.get("local_model_name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        print(f"🧠 Loading local model: {model_id}")

        local_tokenizer = AutoTokenizer.from_pretrained(model_id)
        local_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            device_map="auto"
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
initialize_local_model()


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

    # Inject restriction prompt only if not already present
    restriction_prompt = (
        "You are a highly specialized AI test case generator for the application my.charitableimpact.com.\n"
        "Only generate test automation code in Java using Selenium, TestNG, and Maven following the Page Object Model (POM).\n"
        "Do not respond to unrelated queries. If a question is off-topic, reply with:\n"
        "'❌ I can only help with test case generation for charitableimpact.com using Java + Selenium + TestNG + Maven.'\n"
        "Valid environments include:\n"
        "- https://my.charitableimpact.com (Production)\n"
        "- https://qa.my.charitableimpact.com (QA)\n"
        "- https://stage.my.charitableimpact.com (Stage)"
    )

    if not any(m.get("role") == "system" and "You are a highly specialized AI" in m.get("content", "") for m in prompt_messages):
        prompt_messages.insert(0, {"role": "system", "content": restriction_prompt})

    # Process based on LLM mode
    if llm_mode == "local" and local_model:
        try:
            formatted_input = local_tokenizer.apply_chat_template(
                prompt_messages, tokenize=False, add_generation_prompt=True
            )
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

    end_time = time.time()
    elapsed_time = round(end_time - start_time, 2)

    return final_response, elapsed_time




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
