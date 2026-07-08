from pydantic import BaseModel, field_validator

from app.schemas.validators import SymptomTextValidator


class TriageRequestSchema(BaseModel):
    symptom_text: str
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("symptom_text")
    @classmethod
    def validate_symptoms(cls, v: str) -> str:
        return SymptomTextValidator.validate_symptom_text(v)

    @field_validator("latitude")
    @classmethod
    def validate_lat(cls, v: float | None) -> float | None:
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("Invalid latitude")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_lng(cls, v: float | None) -> float | None:
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("Invalid longitude")
        return v

