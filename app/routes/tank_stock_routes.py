from flask import Blueprint, request
from app.models import TankStock, StockAdjustment
from app import db
from datetime import datetime
from app.utils import api_response, validate_json, paginate_response
from sqlalchemy.orm import joinedload
from app.models.tank import Tank
from app.models.fish_type import FishType

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

    q = TankStock.query.options(
        joinedload(TankStock.tank), 
        joinedload(TankStock.fish_type)
    )

    if tank_id:
        q = q.filter(TankStock.tank_id == tank_id).join(FishType).order_by(FishType.common_name)
    elif fish_type_id:
        q = q.filter(TankStock.fish_type_id == fish_type_id).join(Tank).order_by(Tank.tank_name)
    else:
        q = q.join(Tank).join(FishType).order_by(Tank.tank_name, FishType.common_name)

    stock_list = [ts.to_dict() for ts in q.all()]
    return api_response("Tank stock retrieved successfully", data=stock_list)