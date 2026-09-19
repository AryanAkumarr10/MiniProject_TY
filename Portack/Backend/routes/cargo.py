from flask import Blueprint, request, jsonify
from models import db, Cargo, Vessel

cargo_bp = Blueprint("cargo", __name__, url_prefix="/api")

VALID_STATUSES = {"loaded", "unloaded", "in_yard", "dispatched"}


@cargo_bp.route("/cargo", methods=["GET"])
def list_cargo():
    # Optional filter: /api/cargo?vessel_id=1
    vessel_id = request.args.get("vessel_id", type=int)
    query = Cargo.query
    if vessel_id:
        query = query.filter_by(vessel_id=vessel_id)
    items = query.order_by(Cargo.created_at.desc()).all()
    return jsonify([c.to_dict() for c in items]), 200


@cargo_bp.route("/cargo", methods=["POST"])
def create_cargo():
    data = request.get_json() or {}
    description = data.get("description", "").strip()
    weight_tons = data.get("weight_tons", 0)
    vessel_id = data.get("vessel_id")
    container_number = data.get("container_number")
    yard_location = data.get("yard_location")

    if not description:
        return jsonify({"error": "description is required"}), 400

    if not vessel_id:
        return jsonify({"error": "vessel_id is required"}), 400

    vessel = Vessel.query.get(vessel_id)
    if not vessel:
        return jsonify({"error": "vessel not found"}), 404

    if container_number and Cargo.query.filter_by(container_number=container_number).first():
        return jsonify({"error": "a cargo item with this container number already exists"}), 409

    cargo = Cargo(
        description=description,
        weight_tons=weight_tons,
        vessel_id=vessel_id,
        container_number=container_number,
        yard_location=yard_location,
        status="loaded"
    )
    db.session.add(cargo)
    db.session.commit()

    return jsonify({"message": "cargo recorded", "cargo": cargo.to_dict()}), 201


@cargo_bp.route("/cargo/<int:cargo_id>/status", methods=["PATCH"])
def update_cargo_status(cargo_id):
    cargo = Cargo.query.get(cargo_id)
    if not cargo:
        return jsonify({"error": "cargo item not found"}), 404

    data = request.get_json() or {}
    new_status = data.get("status")
    yard_location = data.get("yard_location")

    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400

    cargo.status = new_status
    if yard_location is not None:
        cargo.yard_location = yard_location

    db.session.commit()
    return jsonify({"message": "cargo status updated", "cargo": cargo.to_dict()}), 200