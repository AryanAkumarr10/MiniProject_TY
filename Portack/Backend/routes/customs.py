from flask import Blueprint, request, jsonify
from models import db, CustomsClearance, Cargo

customs_bp = Blueprint("customs", __name__, url_prefix="/api")

VALID_STATUSES = {"pending", "under_review", "cleared", "rejected"}


@customs_bp.route("/customs", methods=["GET"])
def list_clearances():
    cargo_id = request.args.get("cargo_id", type=int)
    query = CustomsClearance.query
    if cargo_id:
        query = query.filter_by(cargo_id=cargo_id)
    clearances = query.order_by(CustomsClearance.created_at.desc()).all()
    return jsonify([c.to_dict() for c in clearances]), 200


@customs_bp.route("/customs", methods=["POST"])
def create_clearance():
    data = request.get_json() or {}
    cargo_id = data.get("cargo_id")
    shipping_bill_number = data.get("shipping_bill_number")
    manifest_number = data.get("manifest_number")

    if not cargo_id:
        return jsonify({"error": "cargo_id is required"}), 400

    cargo = Cargo.query.get(cargo_id)
    if not cargo:
        return jsonify({"error": "cargo item not found"}), 404

    if CustomsClearance.query.filter_by(cargo_id=cargo_id).first():
        return jsonify({"error": "a customs clearance record already exists for this cargo item"}), 409

    clearance = CustomsClearance(
        cargo_id=cargo_id,
        shipping_bill_number=shipping_bill_number,
        manifest_number=manifest_number,
        status="pending"
    )
    db.session.add(clearance)
    db.session.commit()

    return jsonify({"message": "customs clearance record created", "clearance": clearance.to_dict()}), 201


@customs_bp.route("/customs/<int:clearance_id>/status", methods=["PATCH"])
def update_clearance_status(clearance_id):
    clearance = CustomsClearance.query.get(clearance_id)
    if not clearance:
        return jsonify({"error": "clearance record not found"}), 404

    data = request.get_json() or {}
    new_status = data.get("status")
    remarks = data.get("remarks")

    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400

    clearance.status = new_status
    if remarks is not None:
        clearance.remarks = remarks

    db.session.commit()

    # If cleared, automatically move cargo status to 'dispatched' (ready for release)
    if new_status == "cleared":
        clearance.cargo.status = "dispatched"
        db.session.commit()

    return jsonify({"message": "clearance status updated", "clearance": clearance.to_dict()}), 200