import hashlib


def normalize_code(code: str) -> str:
    """Ignore case, spaces and dashes: 'k7qm 3xpd-9twa' == 'K7QM-3XPD-9TWA'."""
    return "".join(ch for ch in code.upper() if ch.isalnum())


def hash_code(code: str) -> str:
    return hashlib.sha256(normalize_code(code).encode()).hexdigest()