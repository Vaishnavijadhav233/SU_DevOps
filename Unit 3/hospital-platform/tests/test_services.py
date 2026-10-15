import pytest
from app import services
from app.services import ServiceError

FUTURE = "2099-01-15T10:00"


def test_register_duplicate_email_fails(app):
    with app.app_context():
        services.register_user("a@b.com", "secret1")
        with pytest.raises(ServiceError, match="already registered"):
            services.register_user("a@b.com", "secret1")


def test_short_password_rejected(app):
    with app.app_context():
        with pytest.raises(ServiceError, match="at least 6"):
            services.register_user("a@b.com", "123")


def test_double_booking_blocked(app):
    with app.app_context():
        u1 = services.register_user("a@b.com", "secret1")
        u2 = services.register_user("c@d.com", "secret1")
        services.book_appointment(u1.id, 1, FUTURE)
        with pytest.raises(ServiceError, match="already booked"):
            services.book_appointment(u2.id, 1, FUTURE)


def test_past_slot_rejected(app):
    with app.app_context():
        u = services.register_user("a@b.com", "secret1")
        with pytest.raises(ServiceError, match="future"):
            services.book_appointment(u.id, 1, "2000-01-01T10:00")


def test_max_active_appointments(app):
    with app.app_context():
        u = services.register_user("a@b.com", "secret1")
        for hour in (9, 10, 11):
            services.book_appointment(u.id, 1, f"2099-01-15T{hour:02d}:00")
        with pytest.raises(ServiceError, match="max 3"):
            services.book_appointment(u.id, 1, "2099-01-15T12:00")


def test_cancel_frees_slot(app):
    with app.app_context():
        u = services.register_user("a@b.com", "secret1")
        a = services.book_appointment(u.id, 1, FUTURE)
        services.cancel_appointment(u.id, a.id)
        again = services.book_appointment(u.id, 1, FUTURE)
        assert again.status == "BOOKED"
