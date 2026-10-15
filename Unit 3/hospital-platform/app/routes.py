from functools import wraps
import jwt
from flask import Blueprint, request, jsonify, g
from app import services
from app.models import Doctor, Appointment

api_bp = Blueprint("api", __name__)


def auth_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return jsonify(error="missing bearer token"), 401
            try:
                claims = services.decode_token(header[7:])
            except jwt.PyJWTError:
                return jsonify(error="invalid or expired token"), 401
            if role and claims.get("role") != role:
                return jsonify(error="forbidden"), 403
            g.user_id, g.role = int(claims["sub"]), claims["role"]
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@api_bp.errorhandler(services.ServiceError)
def handle_service_error(err):
    return jsonify(error=str(err)), 400


@api_bp.route("/health")
def health():
    return jsonify(status="UP", service="Smart Hospital Platform", version="1.0.0")


@api_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    user = services.register_user(data.get("email"), data.get("password"))
    return jsonify(message="registered", user_id=user.id), 201


@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    return jsonify(token=services.login(data.get("email"), data.get("password")))


@api_bp.route("/doctors", methods=["GET"])
def list_doctors():
    return jsonify([d.to_dict() for d in Doctor.query.all()])


@api_bp.route("/doctors", methods=["POST"])
@auth_required(role="admin")
def create_doctor():
    data = request.get_json(silent=True) or {}
    doctor = services.add_doctor(data.get("name"), data.get("specialization"))
    return jsonify(doctor.to_dict()), 201


@api_bp.route("/appointments", methods=["POST"])
@auth_required()
def book():
    data = request.get_json(silent=True) or {}
    appt = services.book_appointment(g.user_id, data.get("doctor_id"), data.get("slot"))
    return jsonify(appt.to_dict()), 201


@api_bp.route("/appointments", methods=["GET"])
@auth_required()
def my_appointments():
    appts = Appointment.query.filter_by(user_id=g.user_id).all()
    return jsonify([a.to_dict() for a in appts])


@api_bp.route("/appointments/<int:appt_id>", methods=["DELETE"])
@auth_required()
def cancel(appt_id):
    return jsonify(services.cancel_appointment(g.user_id, appt_id).to_dict())
