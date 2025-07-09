# config.py

DEFAULT_BROWSER = "chrome"

def get_target_url(env_choice):
    return {
        "production": "https://my.charitableimpact.com/users/login",
        "qa": "https://qa.charitableimpact.com/users/login",
        "stage": "https://stage.charitableimpact.com/users/login"
    }.get(env_choice.lower(), "https://my.charitableimpact.com/users/login")
