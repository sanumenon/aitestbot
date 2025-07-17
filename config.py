# config.py

DEFAULT_BROWSER = "chrome"

def get_target_url(env_choice):
    return {
        "production": "https://my.charitableimpact.com/users/login",
        "qa": "https://my.qa.charitableimpact.com/users/login",
        "stage": "https://my.stg.charitableimpact.com/users/login"
    }.get(env_choice.lower(), "https://my.stg.charitableimpact.com/users/login")
