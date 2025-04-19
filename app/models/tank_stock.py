from datetime import datetime
from sqlalchemy import event
from app import db
from app.models import StockAdjustment


class TankStock(db.Model):
    """Current inventory quantity for a (tank, species) pair."""

    __tablename__ = "tank_species"
    __table_args__ = (
        db.PrimaryKeyConstraint("tank_id", "species_id"),
    )

    tank_id = db.Column(db.Integer, db.ForeignKey(
        "tanks.tank_id"), nullable=False)
    species_id = db.Column(db.Integer, db.ForeignKey(
        "species.species_id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)

    # Relationships
    tank = db.relationship("Tank", back_populates="stocks")
    species = db.relationship("Species", back_populates="stocks")

    # Helpers -----------------------------------------------------------------
    def to_dict(self):
        return {
            "tankId": self.tank_id,
            "speciesId": self.species_id,
            "quantity": self.quantity,
        }

############################
# AUTOMATIC SYNC LOGIC
############################


@event.listens_for(StockAdjustment, "after_insert")
def _sync_tank_stock(mapper, connection, target):
    """Whenever a StockAdjustment row is inserted, ensure TankStock matches
    ``quantity_after``.

    This runs inside the same DB transaction, so it keeps TankStock and
    StockAdjustment atomically consistent.
    """
    # Build an upsert statement (PostgreSQL ON CONFLICT) to avoid race conditions.
    upsert_sql = (
        "INSERT INTO tank_stock (tank_id, species_id, quantity) "
        "VALUES (:tank_id, :species_id, :qty) "
        "ON CONFLICT (tank_id, species_id) "
        "DO UPDATE SET quantity = EXCLUDED.quantity;"
    )
    connection.execute(
        upsert_sql,
        {"tank_id": target.tank_id, "species_id": target.species_id,
            "qty": target.quantity_after},
    )
