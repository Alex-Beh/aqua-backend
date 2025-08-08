from datetime import datetime
from sqlalchemy import event
from app import db
from app.models import StockAdjustment
from sqlalchemy import text


class TankStock(db.Model):
    """Current inventory quantity for a (tank, fish_type_id) pair."""

    __tablename__ = "tank_inventory"
    __table_args__ = (
        db.PrimaryKeyConstraint("tank_id", "fish_type_id"),
    )

    tank_id = db.Column(db.Integer, db.ForeignKey(
        "tanks.tank_id"), nullable=False)
    fish_type_id = db.Column(db.Integer, db.ForeignKey(
        "fish_types.type_id"), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=db.func.current_timestamp(
    ), onupdate=db.func.current_timestamp())

    tank = db.relationship("Tank", back_populates="stocks")
    fish_type = db.relationship("FishType", back_populates="stocks")

    # Helpers -----------------------------------------------------------------
    def to_dict(self):
        return {
            "tankId": self.tank_id,
            "fishTypeId": self.fish_type_id,
            "quantity": self.quantity,
            "lastUpdated": self.last_updated.isoformat() if self.last_updated else None,
            "tank": self.tank.to_dict() if self.tank else None,  # Include nested tank details
            # Include nested fish_type details
            "fishType": self.fish_type.to_dict() if self.fish_type else None,
        }

    def to_dict_light(self):
        ft = self.fish_type            # shortcut

        return {
            "tankId":       self.tank_id,
            "tankCode":     self.tank.tank_code,
            "tankName":     self.tank.tank_name,
            "fishTypeId":   self.fish_type_id,
            "typeCode":    self.fish_type.type_code,
            "commonName":   self.fish_type.common_name,
            "quantity":     self.quantity,
            "lastUpdated": self.last_updated.isoformat() if self.last_updated else None,
            "fishType": None if ft is None else {
                "typeId":       ft.type_id,
                "typeCode":     ft.type_code,
                "commonName":   ft.common_name,
                "scientificName": ft.scientific_name,
            },
        }

    def to_dict_QR_Purpose(self):
        return {
            "tankId": self.tank_id,
            "fishTypeId": self.fish_type_id,
            "quantity": self.quantity,
            "lastUpdated": self.last_updated.isoformat() if self.last_updated else None,
            # Include nested fish_type details
            "fishType": self.fish_type.to_dict() if self.fish_type else None,
        }

############################
# AUTOMATIC SYNC LOGIC
############################


@event.listens_for(StockAdjustment, "after_insert")
def _sync_tank_stock(mapper, connection, target):
    """Sync tank inventory after a stock adjustment."""
    print(f"DEBUG: Syncing tank stock for tank_id={target.tank_id}, "
          f"fish_type_id={target.fish_type_id}, quantity_after={target.quantity_after}")

    upsert_sql = (
        "INSERT INTO tank_inventory (tank_id, fish_type_id, quantity, last_updated) "
        "VALUES (:tank_id, :fish_type_id, :qty, CURRENT_TIMESTAMP) "
        "ON CONFLICT (tank_id, fish_type_id) "
        "DO UPDATE SET quantity = EXCLUDED.quantity, last_updated = CURRENT_TIMESTAMP;"
    )

    connection.execute(
        text(upsert_sql),
        {
            "tank_id": target.tank_id,
            "fish_type_id": target.fish_type_id,
            "qty": target.quantity_after,
        },
    )
