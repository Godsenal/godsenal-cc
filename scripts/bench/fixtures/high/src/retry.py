import time


def call_with_retry(fn, attempts=3, delay=0.0):
    """Call fn, retrying when it fails. Returns fn's result."""
    for i in range(attempts + 1):
        try:
            return fn()
        except Exception:
            time.sleep(delay)
    return fn()
