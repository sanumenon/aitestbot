import os
import openai
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch
import warnings

warnings.filterwarnings("ignore", message="You are using a model of type mistral.*", category=UserWarning)
warnings.filterwarnings("ignore", message="The model 'MistralForCausalLM'.*", category=UserWarning)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = "gpt-4"

local_tokenizer = None
local_model = None
use_openai = False

try:
    print("Loading local Mistral-7B-Instruct-v0.2...")
    model_id = "mistralai/Mistral-7B-Instruct-v0.2"
    local_tokenizer = AutoTokenizer.from_pretrained(model_id)
    local_model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map="cpu")
    local_chatbot_pipeline = pipeline("text-generation", model=local_model, tokenizer=local_tokenizer)#, device=-1) the model's device is already determined by device_map="cpu", so the pipeline doesn't need (and gets confused by) another device argument.
    print("Local model loaded.")
except Exception as e:
    print(f"Failed to load local model: {e}")
    use_openai = True

if not local_model and OPENAI_API_KEY:
    use_openai = True
    print("Using OpenAI fallback...")
elif not local_model and not OPENAI_API_KEY:
    print("No LLM available.")

openai_client = None
if use_openai:
    try:
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"OpenAI init failed: {e}")
        use_openai = False
## Function to handle chat with LLM
def chat_with_llm(prompt_messages: list, temperature=0.7) -> str:
    if local_model and not use_openai:
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
            print(f"Local inference failed: {e}")
            if use_openai:
                return _chat_with_openai(prompt_messages, temperature)
            return f"Local model failed: {str(e)}"
    elif use_openai:
        return _chat_with_openai(prompt_messages, temperature)
    else:
        return "No LLM available."
## Function to handle OpenAI chat completions
def _chat_with_openai(prompt_messages: list, temperature: float) -> str:
    if not openai_client:
        return "OpenAI client not ready."
    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=prompt_messages,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI failed: {str(e)}"

def simple_chat_prompt(user_prompt: str) -> str:
    return chat_with_llm([
        {"role": "system", "content": "You are a Java+Selenium version 4.2 or higher+TestNG expert assistant."},
        {"role": "user", "content": user_prompt}
    ])