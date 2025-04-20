from flask import Blueprint, request
from app.models import TankStock, StockAdjustment
from app import db
from datetime import datetime
from app.utils import api_response, validate_json, paginate_response

stock_bp = Blueprint("stock_bp", __name__, url_prefix="/api/tank-stock")

# --------------------- Serialization ---------------------
def _serialize_stock(ts: TankStock) -> dict:
    return {
        "tankId": ts.tank_id,
        "fishTypeId": ts.fish_type_id,
        "quantity": ts.quantity,
        "lastUpdated": ts.last_updated.isoformat() if ts.last_updated else None,
    }

# --------------------- Endpoints ---------------------
@stock_bp.route("", methods=["GET"])
def list_stock():
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)
    q = TankStock.query
    if tank_id:
        q = q.filter_by(tank_id=tank_id)
    if fish_type_id:
        q = q.filter_by(fish_type_id=fish_type_id)
    stock_list = [ts.to_dict() for ts in q.all()] 
    return api_response("Tank stock retrieved successfully", data=stock_list)