
from flask import Blueprint, request, jsonify
from datetime import datetime

from app import db
from app.models import StockAdjustment

def _serialize_adjustment(adj: StockAdjustment) -> dict:
    return {
        "adjustmentId": adj.adjustment_id,
        "tankId":       adj.tank_id,
        "speciesId":    adj.species_id,
        "quantityBefore": adj.quantity_before,
        "quantityAfter":  adj.quantity_after,
        "timestamp":      adj.timestamp.isoformat(),
        "reason":         adj.reason,
        "notes":          adj.notes,
    }
# ---------------------------------------------------------------------------
# Stock‑adjustment endpoints ------------------------------------------------
# ---------------------------------------------------------------------------
adjust_bp  = Blueprint("adjust_bp",  __name__, url_prefix="/api/stock-adjustments")

@adjust_bp.route("", methods=["GET"])
def list_adjustments():
    tank_id    = request.args.get("tankId",    type=int)
    species_id = request.args.get("speciesId", type=int)
    since      = request.args.get("since")  # ISO‑8601 strings
    until      = request.args.get("until")

    q = StockAdjustment.query
    if tank_id:
        q = q.filter_by(tank_id=tank_id)
    if species_id:
        q = q.filter_by(species_id=species_id)
    if since:
        q = q.filter(StockAdjustment.timestamp >= since)
    if until:
        q = q.filter(StockAdjustment.timestamp <= until)

    rows = q.order_by(StockAdjustment.timestamp.desc()).all()
    return jsonify([_serialize_adjustment(a) for a in rows])


@adjust_bp.route("/<int:adjustment_id>", methods=["GET"])
def get_adjustment(adjustment_id):
    adj = StockAdjustment.query.get_or_404(adjustment_id)
    return jsonify(_serialize_adjustment(adj))
