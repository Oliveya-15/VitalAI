"""Database tables. Created automatically at startup (see main.py)."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ActivityLog(Base):
    """What a signed-in user did (shown on Profile and History). ref_id points at the related row."""
    __tablename__ = "activity_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(160))
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class Assessment(Base):
    """One saved diagnosis run, owned by a user (user_id). client_id is legacy (pre-login) data."""
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    disease: Mapped[str] = mapped_column(String(32), index=True)
    inputs: Mapped[dict] = mapped_column(JSON)
    probability: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))
    model_name: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Donor(Base):
    __tablename__ = "donors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    blood_group: Mapped[str] = mapped_column(String(3), index=True)
    city: Mapped[str] = mapped_column(String(80), index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_donated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    consent: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class BloodRequest(Base):
    __tablename__ = "blood_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_name: Mapped[str] = mapped_column(String(80))
    blood_group: Mapped[str] = mapped_column(String(3), index=True)
    units: Mapped[int] = mapped_column(Integer, default=1)
    hospital: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(80), index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    urgency: Mapped[str] = mapped_column(String(10), default="normal")  # normal|urgent|critical
    contact_phone: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)  # open|fulfilled|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Ambulance(Base):
    """A provider-registered ambulance. `verified` is set by an admin."""
    __tablename__ = "ambulances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20))
    vehicle_type: Mapped[str] = mapped_column(String(10), default="BLS")  # BLS|ALS|NEONATAL|MORTUARY
    city: Mapped[str] = mapped_column(String(80), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AmbulanceRequest(Base):
    __tablename__ = "ambulance_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(20))
    emergency_type: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(10), default="urgent")
    address: Mapped[str] = mapped_column(String(200), default="")
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(12), default="requested", index=True)
    # requested -> dispatched -> on_the_way -> arrived -> completed | cancelled
    ambulance_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
