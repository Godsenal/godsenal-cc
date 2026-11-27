import time

from src.net.errors import ConnectError, ReadTimeout


class RetryPolicy:
    def __init__(self, attempts=3, retry_on=(ConnectError, ReadTimeout), backoff=0.2, sleep=time.sleep):
        self.attempts, self.retry_on, self.backoff, self.sleep = attempts, retry_on, backoff, sleep

    def run(self, call):
        """call() up to `attempts` times while it raises one of `retry_on`; the last error is raised."""
        for attempt in range(1, self.attempts + 1):
            try:
                return call()
            except self.retry_on:
                if attempt == self.attempts:
                    raise
                self.sleep(self.backoff * 2 ** (attempt - 1))
