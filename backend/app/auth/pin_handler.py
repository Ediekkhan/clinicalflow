import bcrypt


BCRYPT_ROUNDS = 12
COMMON_PINS = {"0000", "1111", "1234", "4321", "2222", "3333"}


def hash_pin(pin: str) -> str:
    if not pin.isdigit() or len(pin) != 4:
        raise ValueError("PIN must be exactly 4 numeric digits")
    if pin in COMMON_PINS:
        raise ValueError("PIN too simple. Choose a less predictable PIN")
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verify_pin(pin: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pin.encode(), hashed.encode())
    except ValueError:
        return False

