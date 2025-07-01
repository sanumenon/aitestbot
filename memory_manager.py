# memory_manager.py
from tinydb import TinyDB, Query

class MemoryManager:
    def __init__(self, db_path='cache/memory.json'):
        self.db = TinyDB(db_path)
        self.latest = ""

    def build_prompt(self, user_input: str, url: str) -> str:
        self.latest = user_input
        return f"Generate Java Selenium 4.2+ test case using TestNG and POM for the task: {user_input} at {url}."

    def latest_user_prompt(self):
        return self.latest

    def save_interaction(self, user_input, response):
        self.db.insert({'input': user_input, 'response': response})
