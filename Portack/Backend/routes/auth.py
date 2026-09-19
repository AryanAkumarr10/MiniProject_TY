from flask import Blueprint, request, jsonify, session
from models import db, User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

VALID_ROLES = {"admin", "staff", "agent", "customs"}

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    requested_role = data.get("role", "agent")

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400


    if requested_role not in VALID_ROLES or requested_role == "admin":
        role = "agent"
    else:
        role = requested_role

    if role not in VALID_ROLES:
        return jsonify({"error": f"role must be one of {sorted(VALID_ROLES)}"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "an account with this email already exists"}), 409

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "registered successfully", "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid email or password"}), 401

    session["user_id"] = user.id
    session["role"] = user.role
    return jsonify({"message": "logged in", "user": user.to_dict()}), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "logged out"}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "not logged in"}), 401
    user = User.query.get(user_id)
    return jsonify({"user": user.to_dict()}), 200