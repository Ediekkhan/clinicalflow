import re
from datetime import date


class PhoneValidator:
    @classmethod
    def validate_nigerian_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[^\d+]", "", v)

        if cleaned.startswith("+234"):
            local = cleaned[4:]
        elif cleaned.startswith("234"):
            local = cleaned[3:]
        elif cleaned.startswith("0"):
            local = cleaned[1:]
        else:
            local = cleaned

        valid_prefixes = [
            "70",
            "71",
            "80",
            "81",
            "90",
            "91",
            "703",
            "706",
            "803",
            "806",
            "810",
            "813",
            "814",
            "816",
            "903",
            "906",
            "913",
            "916",
        ]

        if len(local) != 10:
            raise ValueError(f"Invalid phone number length. Got {len(local)} digits, expected 10")
        if not any(local.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError("Phone number doesn't match a known Nigerian network prefix")

        return f"+234{local}"


class SymptomTextValidator:
    @classmethod
    def validate_symptom_text(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Please describe your symptoms in more detail (minimum 10 characters)")
        if len(v) > 2000:
            raise ValueError("Description too long. Maximum 2000 characters")

        v = re.sub(r"<[^>]+>", "", v)
        injection_patterns = [
            r"ignore\s+(previous|above|all)\s+instructions",
            r"system\s*:\s*you\s+are",
            r"new\s+instructions\s*:",
            r"disregard\s+your",
            r"pretend\s+you\s+are",
            r"act\s+as\s+if",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Invalid input detected. Please describe your symptoms normally.")

        return " ".join(v.split())


class DateOfBirthValidator:
    @classmethod
    def validate_dob(cls, v: date) -> date:
        today = date.today()
        age = (today - v).days / 365.25

        if age < 0:
            raise ValueError("Date of birth cannot be in the future")
        if age > 120:
            raise ValueError("Date of birth is not valid")
        if age < 1:
            raise ValueError("For patients under 1 year old, please register with a guardian")

        return v

