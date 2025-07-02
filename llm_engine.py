import os
import openai
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch
import warnings

warnings.filterwarnings("ignore")

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = "gpt-3.5-turbo"  # Default OpenAI model

# Global variables
local_tokenizer = None
local_model = None
local_chatbot_pipeline = None
openai_client = None
llm_mode = "local"  # Default mode

def initialize_local_model():
    global local_tokenizer, local_model, local_chatbot_pipeline
    try:
        model_id = "mistralai/Mistral-7B-Instruct-v0.2"
        local_tokenizer = AutoTokenizer.from_pretrained(model_id)
        local_model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map="cpu")
        local_chatbot_pipeline = pipeline("text-generation", model=local_model, tokenizer=local_tokenizer)
        print("✅ Local model loaded.")
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

# Call once at startup to attempt local load
initialize_local_model()

def set_llm_mode(mode: str):
    global llm_mode
    if mode == "openai":
        if initialize_openai_client():
            llm_mode = "openai"
        else:
            llm_mode = None
    elif mode == "local":
        if local_model:
            llm_mode = "local"
        else:
            llm_mode = None
    else:
        llm_mode = None
    print(f"🔁 LLM mode set to: {llm_mode}")

def chat_with_llm(prompt_messages: list, temperature=0.7) -> str:
    if llm_mode == "local" and local_model:
        try:
            formatted_input = local_tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
            response = local_chatbot_pipeline(
                formatted_input,
                max_new_tokens=512,
                do_sample=True,
                temperature=temperature,
                pad_token_id=local_tokenizer.eos_token_id
            )[0]["generated_text"]
            return response.replace(formatted_input, "").strip()
        except Exception as e:
            return f"❌ Local model inference failed: {str(e)}"

    elif llm_mode == "openai" and openai_client:
        try:
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL_NAME,
                messages=prompt_messages,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"❌ OpenAI call failed: {str(e)}"
    
    else:
        return "❌ Selected LLM mode is not available or failed to initialize."

def simple_chat_prompt(user_prompt: str) -> str:
    return chat_with_llm([
        {"role": "system", "content": "You are a senior QA automation engineer and expert assistant in Java (version 11+), Selenium 4.2 or higher, and TestNG. You help generate robust, reusable page object model test cases and validate UI behavior for web applications."},
        {"role": "user", "content": user_prompt}
    ])
