import json
import os


class Store:
    """Users keyed by normalized email, loaded from and saved to a JSON file."""

    def __init__(self, path):
        self.path = path
        self.users = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.users = json.load(f)

    def get(self, key):
        return self.users.get(key)

    def put(self, key, user):
        self.users[key] = user
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
