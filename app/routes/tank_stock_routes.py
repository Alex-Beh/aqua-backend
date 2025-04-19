
from flask import Blueprint, request, jsonify
from app.models import TankStock, StockAdjustment
from app import db
from datetime import datetime


def _serialize_stock(ts: TankStock) -> dict:
    return {
        "tankId": ts.tank_id,
        "speciesId": ts.species_id,
        "quantity": ts.quantity,
    }


# ---------------------------------------------------------------------------
# Tank‑stock endpoints ------------------------------------------------------
# ---------------------------------------------------------------------------
stock_bp = Blueprint("stock_bp",   __name__, url_prefix="/api/tank-stock")


@stock_bp.route("", methods=["GET"])
def list_stock():
    tank_id = request.args.get("tankId",    type=int)
    species_id = request.args.get("speciesId", type=int)
    q = TankStock.query
    if tank_id:
        q = q.filter_by(tank_id=tank_id)
    if species_id:
        q = q.filter_by(species_id=species_id)
    return jsonify([_serialize_stock(ts) for ts in q.all()])


@stock_bp.route("", methods=["POST"])
def upsert_stock():
    """Insert or update `TankStock` and log a corresponding `StockAdjustment`."""
    data = request.get_json(force=True)
    tank_id = data["tankId"]
    species_id = data["speciesId"]
    quantity_after = int(data["quantity"])
    reason = data.get("reason", "Manual update")
    notes = data.get("notes")

    ts = TankStock.query.get((tank_id, species_id))
    quantity_before = ts.quantity if ts else 0

    if ts:
        ts.quantity = quantity_after
    else:
        ts = TankStock(tank_id=tank_id, species_id=species_id,
                       quantity=quantity_after)
        db.session.add(ts)

    adj = StockAdjustment(
        tank_id=tank_id,
        species_id=species_id,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        reason=reason,
        notes=notes,
    )
    db.session.add(adj)
    db.session.commit()
    return jsonify(_serialize_stock(ts)), (201 if quantity_before == 0 else 200)
