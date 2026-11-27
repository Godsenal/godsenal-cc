import hashlib

from src.users import normalize_email


def _hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


class DuplicateUser(Exception):
    pass


def signup(store, email, password):
    key = normalize_email(email)
    if store.get(key) is not None:
        raise DuplicateUser(email)
    store.put(key, {"email": email, "pw": _hash(password)})


def login(store, email, password):
    """True when the email belongs to a user with this password."""
    user = store.get(normalize_email(email))
    return user is not None and user["pw"] == _hash(password)
