import itertools

from src.net.transport import Transport


class FakeGateway(Transport):
    """Processes every request it receives and remembers it by Idempotency-Key."""

    def __init__(self):
        self.processed, self.by_key, self.ids = [], {}, itertools.count(1)

    def post(self, path, body, headers):
        key = headers.get("Idempotency-Key")
        if key in self.by_key:
            return self.by_key[key]
        response = {"id": f"{path.strip('/')}_{next(self.ids)}"}
        self.processed.append((path, body))
        self.by_key[key] = response
        return response
