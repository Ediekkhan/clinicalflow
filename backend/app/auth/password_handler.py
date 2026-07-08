import re

import bcrypt


BCRYPT_ROUNDS = 12


def hash_password(plain: str) -> str:
    if len(plain) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", plain):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", plain):
        raise ValueError("Password must contain at least one number")
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False

