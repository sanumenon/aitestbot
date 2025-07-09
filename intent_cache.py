#intent_cache.py
import hashlib
from tinydb import TinyDB, Query
import os
# This file implements a simple intent cache using TinyDB to store and retrieve code snippets based on user prompts.
class IntentCache:
    def __init__(self, db_path='cache/intent_cache.json'):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = TinyDB(db_path)
        self.query = Query()

    def _hash_prompt(self, prompt: str) -> str:
        return hashlib.sha256(prompt.strip().lower().encode()).hexdigest()

    def get_cached(self, prompt: str):
        hash_key = self._hash_prompt(prompt)
        result = self.db.get(self.query.hash == hash_key)
        return result['code'] if result else None

    def store(self, prompt: str, code: str):
        hash_key = self._hash_prompt(prompt)
        if not self.get_cached(prompt):
            self.db.insert({'hash': hash_key, 'prompt': prompt, 'code': code})
            return True
        return False

    def clear_cache(self):
        self.db.truncate()
        return "✅ Cache cleared."

# Usage:
# cache = IntentCache()
# code = cache.get_cached("Login and verify profile")
# if not code:
#     code = generate_test_code(...)
#     cache.store(prompt, code)
