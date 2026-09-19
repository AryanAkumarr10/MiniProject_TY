from flask import Blueprint, jsonify
from models import db, Berth, Vessel, Cargo, Invoice

reports_bp = Blueprint("reports", __name__, url_prefix="/api")

@reports_bp.route("/reports/dashboard", methods=["GET"])
def dashboard():
    total_berths = Berth.query.count()
    occupied_berths = db.session.query(Vessel.berth_id).filter(
        Vessel.status != "departed", Vessel.berth_id.isnot(None)
    ).distinct().count()

    vessel_counts = {
        "scheduled": Vessel.query.filter_by(status="scheduled").count(),
        "berthed": Vessel.query.filter_by(status="berthed").count(),
        "departed": Vessel.query.filter_by(status="departed").count(),
    }

    cargo_counts = {
        "loaded": Cargo.query.filter_by(status="loaded").count(),
        "unloaded": Cargo.query.filter_by(status="unloaded").count(),
        "in_yard": Cargo.query.filter_by(status="in_yard").count(),
        "dispatched": Cargo.query.filter_by(status="dispatched").count(),
    }

    total_cargo_weight = db.session.query(db.func.sum(Cargo.weight_tons)).scalar() or 0

    unpaid_invoices = Invoice.query.filter_by(status="unpaid").count()
    total_revenue = db.session.query(db.func.sum(Invoice.total_amount)).filter(
        Invoice.status == "paid"
    ).scalar() or 0

    return jsonify({
        "berths": {
            "total": total_berths,
            "occupied": occupied_berths,
            "free": total_berths - occupied_berths
        },
        "vessels": vessel_counts,
        "cargo": {
            "by_status": cargo_counts,
            "total_weight_tons": total_cargo_weight
        },
        "billing": {
            "unpaid_invoices": unpaid_invoices,
            "total_revenue": total_revenue
        }
    }), 200