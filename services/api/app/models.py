"""Data model. Key rule from the plan: a User is not a role — roles live in
Membership, so one caregiver can belong to many circles (iteration-2 platform)
and every care row carries circle_id (tenant key)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def uid() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    locale: Mapped[str] = mapped_column(String, default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CareCircle(Base):
    __tablename__ = "care_circles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    recipient_name: Mapped[str] = mapped_column(String)
    recipient_dob: Mapped[str] = mapped_column(String, default="")
    recipient_notes: Mapped[str] = mapped_column(Text, default="")
    consent_recorded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    invite_code: Mapped[str] = mapped_column(String, default=lambda: uuid.uuid4().hex[:8])
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="circle")


class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    circle_id: Mapped[str] = mapped_column(ForeignKey("care_circles.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # owner | member | caregiver | viewer
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    circle: Mapped[CareCircle] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship()


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    circle_id: Mapped[str] = mapped_column(ForeignKey("care_circles.id"), index=True)
    filename: Mapped[str] = mapped_column(String)
    doc_type: Mapped[str] = mapped_column(String, default="unknown")  # classified kind
    storage_path: Mapped[str] = mapped_column(String)
    pages: Mapped[int] = mapped_column(Integer, default=1)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    # pending -> processing -> needs_review -> approved | rejected | needs_clarification
    status: Mapped[str] = mapped_column(String, default="pending")
    reject_reason: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ExtractedItem(Base):
    __tablename__ = "extracted_items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    circle_id: Mapped[str] = mapped_column(ForeignKey("care_circles.id"), index=True)
    kind: Mapped[str] = mapped_column(String)  # medication|appointment|instruction|contact|observation
    payload_json: Mapped[dict] = mapped_column(JSON)
    source_page: Mapped[int] = mapped_column(Integer, default=1)
    source_quote: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    flags: Mapped[list] = mapped_column(JSON, default=list)  # conflict|missing_field|duplicate|low_confidence
    review_status: Mapped[str] = mapped_column(String, default="pending")  # pending|approved|edited|rejected
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class Medication(Base):
    __tablename__ = "medications"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    circle_id: Mapped[str] = mapped_column(ForeignKey("care_circles.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    dose_text: Mapped[str] = mapped_column(String, default="")   # always "as written", never normalised
    schedule_text: Mapped[str] = mapped_column(String, default="")
    source_item_id: Mapped[str | None] = mapped_column(ForeignKey("extracted_items.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    circle_id: Mapped[str] = mapped_column(ForeignKey("care_circles.id"), index=True)
    when_text: Mapped[str] = mapped_column(String)
    where_text: Mapped[str] = mapped_column(String, default="")
    with_whom: Mapped[str] = mapped_column(String, default="")
    what: Mapped[str] = mapped_column(String, default="")
    source_item_id: Mapped[str | None] = mapped_column(ForeignKey("extracted_items.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="upcoming")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    circle_id: Mapped[str] = mapped_column(ForeignKey("care_circles.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    due_text: Mapped[str] = mapped_column(String, default="")
    assignee_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="open")  # open|done
    source: Mapped[str] = mapped_column(String, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class CareUpdate(Base):
    __tablename__ = "care_updates"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    circle_id: Mapped[str] = mapped_column(ForeignKey("care_circles.id"), index=True)
    author_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    audio_path: Mapped[str] = mapped_column(String, default="")
    transcript: Mapped[str] = mapped_column(Text, default="")
    structured_json: Mapped[dict] = mapped_column(JSON, default=dict)
    red_flags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft|confirmed|discarded
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    circle_id: Mapped[str] = mapped_column(ForeignKey("care_circles.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String)  # user|assistant
    content: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[list] = mapped_column(JSON, default=list)
    route: Mapped[str] = mapped_column(String, default="")  # record_fact|general_care|clinical|out_of_scope|blocked
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    circle_id: Mapped[str] = mapped_column(ForeignKey("care_circles.id"), index=True)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String)
    entity: Mapped[str] = mapped_column(String)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime, default=now)


# --- Iteration 2 (caregiver marketplace), reserved now so no migration later ---
class CaregiverProfile(Base):
    __tablename__ = "caregiver_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    languages: Mapped[list] = mapped_column(JSON, default=list)
    services: Mapped[list] = mapped_column(JSON, default=list)
    hourly_rate: Mapped[float | None] = mapped_column(Float, nullable=True)


class CareRequest(Base):
    __tablename__ = "care_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    circle_id: Mapped[str] = mapped_column(ForeignKey("care_circles.id"), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    schedule: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="open")
