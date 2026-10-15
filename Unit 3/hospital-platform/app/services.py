import os
import datetime as dt
import jwt
from flask import current_app
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import User, Doctor, Appointment

MAX_ACTIVE_APPOINTMENTS = 3


class ServiceError(ValueError):
    """Business-rule violation (mapped to HTTP 400)."""


def seed_data():
    try:
        if not User.query.filter_by(email="admin@hospital.com").first():
            admin = User(email="admin@hospital.com", role="admin")
            admin.set_password(os.environ.get("ADMIN_PASSWORD", "admin123"))
            db.session.add(admin)
        if Doctor.query.count() == 0:
            db.session.add_all([
                Doctor(name="Dr. Asha Patil", specialization="Cardiology"),
                Doctor(name="Dr. Rahul Verma", specialization="Dermatology"),
            ])
        db.session.commit()
    except IntegrityError:
        db.session.rollback()


def register_user(email, password):
    if not email or not password:
        raise ServiceError("email and password are required")
    if len(password) < 6:
        raise ServiceError("password must be at least 6 characters")
    if User.query.filter_by(email=email).first():
        raise ServiceError("email already registered")
    user = User(email=email, role="patient")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def login(email, password):
    user = User.query.filter_by(email=email or "").first()
    if not user or not user.check_password(password or ""):
        raise ServiceError("invalid credentials")
    payload = {"sub": str(user.id), "role": user.role,
               "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def decode_token(token):
    return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])


def add_doctor(name, specialization):
    if not name or not specialization:
        raise ServiceError("name and specialization are required")
    doctor = Doctor(name=name, specialization=specialization)
    db.session.add(doctor)
    db.session.commit()
    return doctor


def book_appointment(user_id, doctor_id, slot_iso):
    if not db.session.get(Doctor, doctor_id):
        raise ServiceError("doctor not found")
    try:
        slot = dt.datetime.fromisoformat(slot_iso)
    except (TypeError, ValueError):
        raise ServiceError("slot must be ISO format, e.g. 2030-01-15T10:00")
    if slot.tzinfo:
        slot = slot.astimezone(dt.timezone.utc).replace(tzinfo=None)
    if slot <= dt.datetime.now():
        raise ServiceError("slot must be in the future")
    if Appointment.query.filter_by(doctor_id=doctor_id, slot=slot, status="BOOKED").first():
        raise ServiceError("slot already booked for this doctor")
    active = Appointment.query.filter_by(user_id=user_id, status="BOOKED").count()
    if active >= MAX_ACTIVE_APPOINTMENTS:
        raise ServiceError(f"max {MAX_ACTIVE_APPOINTMENTS} active appointments allowed")
    appt = Appointment(user_id=user_id, doctor_id=doctor_id, slot=slot)
    db.session.add(appt)
    db.session.commit()
    return appt


def cancel_appointment(user_id, appointment_id):
    appt = db.session.get(Appointment, appointment_id)
    if not appt or appt.user_id != user_id:
        raise ServiceError("appointment not found")
    if appt.status != "BOOKED":
        raise ServiceError("only BOOKED appointments can be cancelled")
    appt.status = "CANCELLED"
    db.session.commit()
    return appt
