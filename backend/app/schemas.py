import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.services.blood_service import GROUPS

Group = Literal["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]


def _phone(v: str) -> str:
    digits = re.sub(r"[\s\-()]", "", v)
    if not re.fullmatch(r"\+?\d{7,15}", digits):
        raise ValueError("Enter a valid phone number (7-15 digits).")
    return digits


class PredictIn(BaseModel):
    values: dict[str, float]


class DonorIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str
    blood_group: Group
    city: str = Field(min_length=2, max_length=80)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    last_donated: datetime | None = None
    consent: bool

    _p = field_validator("phone")(_phone)

    @field_validator("consent")
    @classmethod
    def _must_consent(cls, v):
        if not v:
            raise ValueError("Consent to be contacted for blood requests is required.")
        return v


class OptOutIn(BaseModel):
    phone: str
    _p = field_validator("phone")(_phone)


class BloodRequestIn(BaseModel):
    patient_name: str = Field(min_length=2, max_length=80)
    blood_group: Group
    units: int = Field(default=1, ge=1, le=10)
    hospital: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=80)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    urgency: Literal["normal", "urgent", "critical"] = "normal"
    contact_phone: str
    note: str = Field(default="", max_length=400)

    _p = field_validator("contact_phone")(_phone)


class StatusIn(BaseModel):
    status: Literal["open", "fulfilled", "cancelled"]


class TriageIn(BaseModel):
    text: str = Field(min_length=2, max_length=1500)


class AmbulanceIn(BaseModel):
    operator: str = Field(min_length=2, max_length=100)
    phone: str
    vehicle_type: Literal["BLS", "ALS", "NEONATAL", "MORTUARY"] = "BLS"
    city: str = Field(min_length=2, max_length=80)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    _p = field_validator("phone")(_phone)


class AmbulanceRequestIn(BaseModel):
    patient_name: str = Field(min_length=2, max_length=80)
    phone: str
    emergency_type: str = Field(min_length=2, max_length=60)
    severity: Literal["urgent", "critical"] = "urgent"
    address: str = Field(default="", max_length=200)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    _p = field_validator("phone")(_phone)


class AmbulanceStatusIn(BaseModel):
    status: Literal["requested", "dispatched", "on_the_way", "arrived", "completed", "cancelled"]
    ambulance_id: int | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    history: list[ChatMessage] = []
    lat: float | None = None
    lon: float | None = None


class BMIIn(BaseModel):
    weight_kg: float = Field(gt=10, lt=400)
    height_cm: float = Field(gt=50, lt=260)


class BPIn(BaseModel):
    systolic: int
    diastolic: int


class ReportIn(BaseModel):
    text: str = Field(min_length=3, max_length=6000)
    sex: str | None = None


# ----------------------------------------------------------------- auth
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=160)
    password: str = Field(max_length=128)
    phone: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return " ".join(v.split())

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        v = v.strip().lower()
        if not _EMAIL.match(v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("phone")
    @classmethod
    def _ph(cls, v):
        return _phone(v) if v else None


class LoginIn(BaseModel):
    email: str = Field(max_length=160)
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return v.strip().lower()


class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str | None = None
    city: str | None = Field(default=None, max_length=80)
    blood_group: Group | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return " ".join(v.split())

    @field_validator("phone")
    @classmethod
    def _ph(cls, v):
        return _phone(v) if v else None

    @field_validator("city")
    @classmethod
    def _city(cls, v):
        return v.strip() or None if v else None


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


class DeleteAccountIn(BaseModel):
    password: str = Field(max_length=128)
