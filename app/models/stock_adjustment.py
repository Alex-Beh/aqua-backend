from app import db
from datetime import datetime

class StockAdjustment(db.Model):
    """Historical log of every change to TankStock."""

    __tablename__ = "stock_adjustments"

    adjustment_id = db.Column(db.Integer, primary_key=True)
    tank_id = db.Column(db.Integer, db.ForeignKey("tanks.tank_id"), nullable=False)
    species_id = db.Column(db.Integer, db.ForeignKey("species.species_id"), nullable=False)

    quantity_before = db.Column(db.Integer, nullable=False)
    quantity_after = db.Column(db.Integer, nullable=False)

    reason = db.Column(db.String(255))  # e.g. Mortality, Addition, Transfer
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships (plain ForeignKey; no backref needed but you can add if desired)

    # Helpers -----------------------------------------------------------------
    def to_dict(self):
        return {
            "adjustmentId": self.adjustment_id,
            "tankId": self.tank_id,
            "speciesId": self.species_id,
            "quantityBefore": self.quantity_before,
            "quantityAfter": self.quantity_after,
            "reason": self.reason,
            "notes": self.notes,
            "timestamp": self.timestamp.isoformat(),
        }
