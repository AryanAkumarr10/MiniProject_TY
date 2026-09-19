from flask import Blueprint, request, jsonify, session
from datetime import datetime
from models import db, Berth, Vessel

vessels_bp = Blueprint("vessels", __name__, url_prefix="/api")


# ---------- Berths ----------

@vessels_bp.route("/berths", methods=["GET"])
def list_berths():
    berths = Berth.query.all()
    return jsonify([b.to_dict() for b in berths]), 200


@vessels_bp.route("/berths", methods=["POST"])
def create_berth():
    data = request.get_json() or {}
    code = data.get("code", "").strip()
    capacity = data.get("capacity_tons", 0)

    if not code:
        return jsonify({"error": "berth code is required"}), 400

    if Berth.query.filter_by(code=code).first():
        return jsonify({"error": "a berth with this code already exists"}), 409

    berth = Berth(code=code, capacity_tons=capacity)
    db.session.add(berth)
    db.session.commit()
    return jsonify({"message": "berth created", "berth": berth.to_dict()}), 201


# ---------- Vessels ----------

def _parse_datetime(value, field_name):
    """Helper: converts an ISO string like '2026-07-15T10:00' into a datetime object."""
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid ISO datetime string, e.g. 2026-07-15T10:00")


@vessels_bp.route("/vessels", methods=["GET"])
def list_vessels():
    vessels = Vessel.query.order_by(Vessel.arrival_time).all()
    return jsonify([v.to_dict() for v in vessels]), 200


@vessels_bp.route("/vessels", methods=["POST"])
def create_vessel():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    imo_number = data.get("imo_number")
    vessel_type = data.get("vessel_type", "cargo")
    berth_id = data.get("berth_id")

    if not name:
        return jsonify({"error": "vessel name is required"}), 400

    try:
        arrival_time = _parse_datetime(data.get("arrival_time"), "arrival_time")
        departure_time = _parse_datetime(data.get("departure_time"), "departure_time")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if departure_time <= arrival_time:
        return jsonify({"error": "departure_time must be after arrival_time"}), 400

    # ---- Conflict detection ----
    if berth_id:
        berth = Berth.query.get(berth_id)
        if not berth:
            return jsonify({"error": "berth not found"}), 404

        # Check for any existing vessel at this berth whose time window overlaps
        conflict = Vessel.query.filter(
            Vessel.berth_id == berth_id,
            Vessel.status != "departed",
            Vessel.arrival_time < departure_time,
            Vessel.departure_time > arrival_time
        ).first()

        if conflict:
            return jsonify({
                "error": f"berth conflict: vessel '{conflict.name}' already occupies berth "
                         f"'{berth.code}' from {conflict.arrival_time.isoformat()} "
                         f"to {conflict.departure_time.isoformat()}"
            }), 409

    vessel = Vessel(
        name=name,
        imo_number=imo_number,
        vessel_type=vessel_type,
        berth_id=berth_id,
        arrival_time=arrival_time,
        departure_time=departure_time,
        status="scheduled"
    )
    db.session.add(vessel)
    db.session.commit()

    return jsonify({"message": "vessel scheduled", "vessel": vessel.to_dict()}), 201


@vessels_bp.route("/vessels/<int:vessel_id>/status", methods=["PATCH"])
def update_vessel_status(vessel_id):
    vessel = Vessel.query.get(vessel_id)
    if not vessel:
        return jsonify({"error": "vessel not found"}), 404

    data = request.get_json() or {}
    new_status = data.get("status")

    if new_status not in {"scheduled", "berthed", "departed"}:
        return jsonify({"error": "status must be one of: scheduled, berthed, departed"}), 400

    vessel.status = new_status
    db.session.commit()
    return jsonify({"message": "status updated", "vessel": vessel.to_dict()}), 200
@vessels_bp.route("/berths/<int:berth_id>", methods=["DELETE"])
def delete_berth(berth_id):
    if session.get("role") != "admin":
        return jsonify({"error": "only an admin can delete berths"}), 403

    berth = Berth.query.get(berth_id)
    if not berth:
        return jsonify({"error": "berth not found"}), 404

    # Safety check: don't allow deleting a berth that's currently in use
    active_vessel = Vessel.query.filter(
        Vessel.berth_id == berth_id, Vessel.status != "departed"
    ).first()
    if active_vessel:
        return jsonify({
            "error": f"cannot delete: vessel '{active_vessel.name}' is currently assigned to this berth"
        }), 409

    db.session.delete(berth)
    db.session.commit()
    return jsonify({"message": "berth deleted"}), 200