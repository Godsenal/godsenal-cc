import hashlib
import hmac


def valid_signature(secret, body, signature):
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
