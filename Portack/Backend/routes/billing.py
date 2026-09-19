from flask import Blueprint, request, jsonify, session
from models import db, Invoice, Vessel, Cargo

billing_bp = Blueprint("billing", __name__, url_prefix="/api")

# --- Simple rate table (per your synopsis: charges based on vessel type, cargo volume, duration of stay) ---
BERTH_HIRE_RATE_PER_HOUR = {
    "cargo": 500,
    "container": 700,
    "tanker": 900,
    "passenger": 400,
}
DEFAULT_BERTH_RATE = 500

CARGO_HANDLING_RATE_PER_TON = 50
STORAGE_RATE_PER_TON_PER_DAY = 10  # applied to cargo currently sitting "in_yard"


@billing_bp.route("/invoices", methods=["GET"])
def list_invoices():
    vessel_id = request.args.get("vessel_id", type=int)
    query = Invoice.query
    if vessel_id:
        query = query.filter_by(vessel_id=vessel_id)
    invoices = query.order_by(Invoice.generated_at.desc()).all()
    return jsonify([i.to_dict() for i in invoices]), 200


@billing_bp.route("/invoices/generate", methods=["POST"])
def generate_invoice():
    data = request.get_json() or {}
    vessel_id = data.get("vessel_id")

    if not vessel_id:
        return jsonify({"error": "vessel_id is required"}), 400

    vessel = Vessel.query.get(vessel_id)
    if not vessel:
        return jsonify({"error": "vessel not found"}), 404

    # --- Berth hire charge: duration of stay x hourly rate for vessel type ---
    duration_hours = (vessel.departure_time - vessel.arrival_time).total_seconds() / 3600
    rate = BERTH_HIRE_RATE_PER_HOUR.get(vessel.vessel_type, DEFAULT_BERTH_RATE)
    berth_hire_charge = round(duration_hours * rate, 2)

    # --- Cargo handling charge: total weight of all cargo linked to this vessel ---
    cargo_items = Cargo.query.filter_by(vessel_id=vessel_id).all()
    total_weight = sum(c.weight_tons for c in cargo_items)
    cargo_handling_charge = round(total_weight * CARGO_HANDLING_RATE_PER_TON, 2)

    # --- Storage charge: only for cargo currently sitting in the yard, flat 1-day estimate ---
    yard_weight = sum(c.weight_tons for c in cargo_items if c.status == "in_yard")
    storage_charge = round(yard_weight * STORAGE_RATE_PER_TON_PER_DAY, 2)

    total_amount = round(berth_hire_charge + cargo_handling_charge + storage_charge, 2)

    invoice = Invoice(
        vessel_id=vessel_id,
        berth_hire_charge=berth_hire_charge,
        cargo_handling_charge=cargo_handling_charge,
        storage_charge=storage_charge,
        total_amount=total_amount,
        status="unpaid"
    )
    db.session.add(invoice)
    db.session.commit()

    return jsonify({"message": "invoice generated", "invoice": invoice.to_dict()}), 201


@billing_bp.route("/invoices/<int:invoice_id>/pay", methods=["PATCH"])
def mark_invoice_paid(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "invoice not found"}), 404

    invoice.status = "paid"
    db.session.commit()
    return jsonify({"message": "invoice marked as paid", "invoice": invoice.to_dict()}), 200
@billing_bp.route("/invoices/<int:invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id):
    if session.get("role") != "admin":
        return jsonify({"error": "only an admin can delete invoices"}), 403

    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "invoice not found"}), 404

    db.session.delete(invoice)
    db.session.commit()
    return jsonify({"message": "invoice deleted"}), 200