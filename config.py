# config.py

DEFAULT_BROWSER = "chrome"

def get_target_url(env_choice):
    return {
        "production": "https://my.charitableimpact.com",
        "qa": "https://qa.charitableimpact.com",
        "stage": "https://stage.charitableimpact.com"
    }.get(env_choice.lower(), "https://my.charitableimpact.com")
