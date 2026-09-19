from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # role: 'admin', 'staff', 'agent', 'customs'
    role = db.Column(db.String(20), nullable=False, default="agent")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role
        }
class Berth(db.Model):
    __tablename__ = "berths"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)   # e.g. "B1", "B2"
    capacity_tons = db.Column(db.Float, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "capacity_tons": self.capacity_tons,
            "is_active": self.is_active
        }


class Vessel(db.Model):
    __tablename__ = "vessels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    imo_number = db.Column(db.String(50), unique=True, nullable=True)  # ship's ID number
    vessel_type = db.Column(db.String(50), nullable=False, default="cargo")

    berth_id = db.Column(db.Integer, db.ForeignKey("berths.id"), nullable=True)
    berth = db.relationship("Berth", backref="vessels")

    arrival_time = db.Column(db.DateTime, nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)

    # status: 'scheduled', 'berthed', 'departed'
    status = db.Column(db.String(20), nullable=False, default="scheduled")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "imo_number": self.imo_number,
            "vessel_type": self.vessel_type,
            "berth_id": self.berth_id,
            "berth_code": self.berth.code if self.berth else None,
            "arrival_time": self.arrival_time.isoformat(),
            "departure_time": self.departure_time.isoformat(),
            "status": self.status
        }
class Cargo(db.Model):
    __tablename__ = "cargo"

    id = db.Column(db.Integer, primary_key=True)
    container_number = db.Column(db.String(50), unique=True, nullable=True)
    description = db.Column(db.String(200), nullable=False)
    weight_tons = db.Column(db.Float, nullable=False, default=0)

    vessel_id = db.Column(db.Integer, db.ForeignKey("vessels.id"), nullable=False)
    vessel = db.relationship("Vessel", backref="cargo_items")

    # status: 'loaded', 'unloaded', 'in_yard', 'dispatched'
    status = db.Column(db.String(20), nullable=False, default="loaded")

    yard_location = db.Column(db.String(50), nullable=True)  # e.g. "Yard-A-12"

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "container_number": self.container_number,
            "description": self.description,
            "weight_tons": self.weight_tons,
            "vessel_id": self.vessel_id,
            "vessel_name": self.vessel.name if self.vessel else None,
            "status": self.status,
            "yard_location": self.yard_location,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    vessel_id = db.Column(db.Integer, db.ForeignKey("vessels.id"), nullable=False)
    vessel = db.relationship("Vessel", backref="invoices")

    berth_hire_charge = db.Column(db.Float, nullable=False, default=0)
    cargo_handling_charge = db.Column(db.Float, nullable=False, default=0)
    storage_charge = db.Column(db.Float, nullable=False, default=0)
    total_amount = db.Column(db.Float, nullable=False, default=0)

    # status: 'unpaid', 'paid'
    status = db.Column(db.String(20), nullable=False, default="unpaid")

    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "vessel_id": self.vessel_id,
            "vessel_name": self.vessel.name if self.vessel else None,
            "berth_hire_charge": self.berth_hire_charge,
            "cargo_handling_charge": self.cargo_handling_charge,
            "storage_charge": self.storage_charge,
            "total_amount": self.total_amount,
            "status": self.status,
            "generated_at": self.generated_at.isoformat()
        }
class CustomsClearance(db.Model):
    __tablename__ = "customs_clearances"

    id = db.Column(db.Integer, primary_key=True)
    cargo_id = db.Column(db.Integer, db.ForeignKey("cargo.id"), nullable=False, unique=True)
    cargo = db.relationship("Cargo", backref=db.backref("customs_clearance", uselist=False))

    shipping_bill_number = db.Column(db.String(50), nullable=True)
    manifest_number = db.Column(db.String(50), nullable=True)

    # status: 'pending', 'under_review', 'cleared', 'rejected'
    status = db.Column(db.String(20), nullable=False, default="pending")
    remarks = db.Column(db.String(300), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "cargo_id": self.cargo_id,
            "cargo_description": self.cargo.description if self.cargo else None,
            "shipping_bill_number": self.shipping_bill_number,
            "manifest_number": self.manifest_number,
            "status": self.status,
            "remarks": self.remarks,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }