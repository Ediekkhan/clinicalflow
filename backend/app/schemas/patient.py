import re
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.validators import DateOfBirthValidator, PhoneValidator


class PatientSignupSchema(BaseModel):
    full_name: str
    phone: str
    date_of_birth: date
    gender: Literal["MALE", "FEMALE", "OTHER"]
    password: str
    latitude: float | None = None
    longitude: float | None = None
    lat: float | None = None
    lng: float | None = None

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name too short")
        if len(v) > 100:
            raise ValueError("Name too long")
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError("Name can only contain letters, spaces, hyphens, and apostrophes")
        return v.title()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return PhoneValidator.validate_nigerian_phone(v)

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        return DateOfBirthValidator.validate_dob(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("latitude", "lat")
    @classmethod
    def validate_lat(cls, v: float | None) -> float | None:
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("Invalid latitude")
        return v

    @field_validator("longitude", "lng")
    @classmethod
    def validate_lng(cls, v: float | None) -> float | None:
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("Invalid longitude")
        return v


class PatientLoginSchema(BaseModel):
    phone: str
    password: str = Field(min_length=8)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return PhoneValidator.validate_nigerian_phone(v)


class SpecialistLoginSchema(BaseModel):
    email: str
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Enter a valid email address")
        return v


class StaffLoginSchema(BaseModel):
    tenant_id: UUID
    staff_id: UUID
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not re.match(r"^\d{4}$", v):
            raise ValueError("PIN must be exactly 4 numeric digits")
        return v


class DeletionRequestSchema(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)

