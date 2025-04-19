from app import db
from datetime import datetime

class StockAdjustment(db.Model):
    """Historical log of every change to TankStock."""

    __tablename__ = "stock_adjustments"

    stock_adjustment_id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'IN', 'OUT', 'TRANSFER', etc. Mortality, Addition, Transfer
    source_tank_id = db.Column(db.Integer, db.ForeignKey("tanks.tank_id"))
    target_tank_id = db.Column(db.Integer, db.ForeignKey("tanks.tank_id"))
    fish_type_id = db.Column(db.Integer, db.ForeignKey("fish_types.type_id"), nullable=False)

    quantity_before = db.Column(db.Integer, nullable=False)
    quantity_after = db.Column(db.Integer, nullable=False)

    reason = db.Column(db.String(255))  # e.g. REMOVAL, DEATH, ADDITION, TRANSFER, STOCK_TAKE
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reference_doc = db.Column(db.String(100))  # Proof or Receipt Number
    notes = db.Column(db.Text)

    # recorded_by = db.Column(db.Integer, db.ForeignKey("app_users.user_id"), nullable=False)
    # recorded_by_signature = db.Column(db.LargeBinary)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # verified_by = db.Column(db.Integer, db.ForeignKey("app_users.user_id"))
    # verified_by_signature = db.Column(db.LargeBinary)
    verified_at = db.Column(db.DateTime)

    is_voided = db.Column(db.Boolean, default=False)
    void_reason = db.Column(db.Text)

    previous_adjustment_id = db.Column(db.Integer, db.ForeignKey("stock_adjustments.stock_adjustment_id"))
    version_number = db.Column(db.Integer, default=1)

    # updated_by = db.Column(db.Integer, db.ForeignKey("app_users.user_id"))
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships (plain ForeignKey; no backref needed but you can add if desired)

    @property
    def quantity_change(self):
        return self.quantity_after - self.quantity_before

    # Helpers -----------------------------------------------------------------
    def to_dict(self):
        return {
            "stockAdjustmentId": self.stock_adjustment_id,
            "sourceTankId": self.source_tank_id,
            "targetTankId": self.target_tank_id,
            "fishTypeId": self.fish_type_id,
            "quantityBefore": self.quantity_before,
            "quantityAfter": self.quantity_after,
            "quantityChange": self.quantity_change,  # Include quantity change
            "transactionType": self.transaction_type,
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