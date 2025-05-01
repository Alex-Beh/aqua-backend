from app import db
from datetime import datetime

class StockAdjustment(db.Model):
    """Historical log of every change to TankStock."""

    __tablename__ = "stock_adjustments"

    stock_adjustment_id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(20), nullable=False)   # ADDITION, REMOVAL, DEATH, TRANSFER, STOCK_TAKE
    tank_id = db.Column(db.Integer, db.ForeignKey("tanks.tank_id"))
    fish_type_id = db.Column(db.Integer, db.ForeignKey("fish_types.type_id"), nullable=False)

    quantity_before = db.Column(db.Integer, nullable=False)
    quantity_after = db.Column(db.Integer, nullable=False)

    reason = db.Column(db.String(255))   # Optional explanation
    transaction_date = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    reference_doc = db.Column(db.String(100))  # Proof or Receipt Number
    notes = db.Column(db.Text)  # Optional explanation

    recorded_by = db.Column(db.String(100))
    # recorded_by_signature = db.Column(db.LargeBinary)
    recorded_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    verified_by = db.Column(db.String(100))
    # verified_by_signature = db.Column(db.LargeBinary)
    verified_at = db.Column(db.DateTime)

    is_voided = db.Column(db.Boolean, default=False)
    void_reason = db.Column(db.Text)

    previous_adjustment_id = db.Column(db.Integer, db.ForeignKey("stock_adjustments.stock_adjustment_id"))
    version_number = db.Column(db.Integer, default=1)

    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())

    # Relationships (plain ForeignKey; no backref needed but you can add if desired)
    tank = db.relationship("Tank", lazy="joined")
    fish_type = db.relationship("FishType", lazy="joined")

    @property
    def quantity_change(self):
        return self.quantity_after - self.quantity_before

    @property
    def direction(self):
        if self.quantity_change > 0:
            return "IN"
        elif self.quantity_change < 0:
            return "OUT"
        else:
            return "SAME"
        
    # Helpers -----------------------------------------------------------------
    def to_dict(self):
        return {
            "stockAdjustmentId": self.stock_adjustment_id,
            "tankId": self.tank_id,
            "tank": self.tank.to_dict() if self.tank else None,
            "fishTypeId": self.fish_type_id,
            "fishType": self.fish_type.to_dict() if self.fish_type else None,
            "quantityBefore": self.quantity_before,
            "quantityAfter": self.quantity_after,
            "quantityChange": self.quantity_change,  # Include quantity change
            "transactionType": self.transaction_type,
            "direction": self.direction,
            "reason": self.reason,
            "notes": self.notes,
            "transactionDate": self.transaction_date.isoformat(),
            "referenceDoc": self.reference_doc,
            "recordedAt": self.recorded_at.isoformat() if self.recorded_at else None,
            "verifiedAt": self.verified_at.isoformat() if self.verified_at else None,
            "isVoided": self.is_voided,
            "voidReason": self.void_reason,
            "previousAdjustmentId": self.previous_adjustment_id,
            "versionNumber": self.version_number,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }