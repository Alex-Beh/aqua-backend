from flask import Blueprint, redirect, abort, current_app
from app import db
from app.services.tank_stock_service import TankStockService
from app.utils import api_response
from app.models import Tank, TankStock, FishType
from app.utils import api_response
from sqlalchemy import func

bp = Blueprint("redirect", __name__, url_prefix="/r")

public_qr_tank = Blueprint("public_tank", __name__, url_prefix="/api/public")

@public_qr_tank.route("/tank/<string:tank_code>", methods=["GET"])
def get_public_tank_details(tank_code):
    """Return tank and fish info for public QR view"""
    tank = Tank.query.filter(func.lower(Tank.tank_code) == tank_code.lower()).first()
    if not tank:
        return api_response(f"Tank with code '{tank_code}' not found", status_code=404)

    stock_list = TankStockService.get_all_tank_stock(tank_id=tank.tank_id).all()

    fish_info_list = []
    for stock in stock_list:
        fish_type = stock.fish_type

        # 🔍 Find other tanks that also contain this fish (exclude the current tank)
        same_fish_stocks = TankStockService.get_all_tank_stock(
            fish_type_id=fish_type.type_id,
            site_id=tank.site_id  # restrict to same site
        ).all()

        same_fish_tanks = [
            {
                "tankCode": s.tank.tank_code,
                "tankName": s.tank.tank_name,
                "quantity": s.quantity
            }
            for s in same_fish_stocks
            if (
                s.tank_id != tank.tank_id and
                (s.tank.status or "").lower() == "active" and
                s.quantity > 0
            )        
        ]

        fish_info_list.append({
            "fishType": fish_type.to_dict_QR_Purpose(),
            "quantity": stock.quantity,
            "sameFishTanks": same_fish_tanks
        })

    response_data = {
        "tank": tank.to_dict_QR_Purpose(),
        "fishList": fish_info_list
    }

    return api_response("Public QR Tank retrieved successfully", data=response_data)
