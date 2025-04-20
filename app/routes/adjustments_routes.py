
from flask import Blueprint, request, jsonify
from datetime import datetime

from app import db
from app.models import StockAdjustment
from app.utils import api_response, validate_json, paginate_response

# ---------------------------------------------------------------------------
# Stock‑adjustment endpoints ------------------------------------------------
# ---------------------------------------------------------------------------
adjust_bp  = Blueprint("adjust_bp",  __name__, url_prefix="/api/stock-adjustments")

@adjust_bp.route("", methods=["GET"])
def list_adjustments():
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)  # Updated to fish_type_id
    since = request.args.get("since")  # ISO‑8601 strings
    until = request.args.get("until")

    q = StockAdjustment.query
    if tank_id:
        q = q.filter_by(tank_id=tank_id)
    if fish_type_id:
        q = q.filter_by(fish_type_id=fish_type_id)
    if since:
        q = q.filter(StockAdjustment.transaction_date >= since)
    if until:
        q = q.filter(StockAdjustment.transaction_date <= until)

    rows = q.order_by(StockAdjustment.transaction_date.desc()).all()
    return api_response("Stock adjustments retrieved successfully", data=[adj.to_dict() for adj in rows])

@adjust_bp.route("/<int:adjustment_id>", methods=["GET"])
def get_adjustment(adjustment_id):
    adj = StockAdjustment.query.get(adjustment_id)
    return api_response("Stock adjustment retrieved successfully", data=adj.to_dict())
