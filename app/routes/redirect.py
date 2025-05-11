from flask import Blueprint, redirect, abort, current_app
from app import db
from app import config   # adjust if you use an app factory pattern
from app.services.tank_stock_service import TankStockService
from app.utils import api_response
from app.models import Tank, TankStock, FishType
from app.utils import api_response

bp = Blueprint("redirect", __name__, url_prefix="/r")

@bp.route("/<code>")
def get_redirect_url(code: str):
    """Return the target URL for the given QR code in JSON payload"""
    url = config.URL_MAP.get(code)
    if url:
        print(f"{code} maps to: {url}")
        return api_response("Redirect URL retrieved", data={"url": url})
    return abort(404, description="QR code target not found")

public_qr_tank = Blueprint("public_tank", __name__, url_prefix="/api/public")

@public_qr_tank.route("/tank/<string:tank_code>", methods=["GET"])
def get_public_tank_details(tank_code):
    """Return tank and fish info for public QR view"""

    tank = Tank.query.filter_by(tank_code=tank_code).first()
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
            if s.tank_id != tank.tank_id and (s.tank.status or "").lower() == "active"
        ]

        fish_info_list.append({
            "fishType": fish_type.to_dict(include_image_data=True),
            "quantity": stock.quantity,
            "sameFishTanks": same_fish_tanks
        })

    response_data = {
        "tank": tank.to_dict(),
        "fishList": fish_info_list
    }

    return api_response("Public QR Tank retrieved successfully", data=response_data)


# @public_qr_tank.route("/tank/<string:tank_code>", methods=["GET"])
# def get_public_tank_details(tank_code):
#     """Return tank and fish details for public QR view"""
#     tank = Tank.query.filter_by(tank_code=tank_code).first()
#     if not tank:
#         return api_response("Tank not found", status_code=404)

#     tank_stock = TankStock.query.filter_by(tank_id=tank.tank_id).first()
#     fish = FishType.query.get(tank_stock.type_id) if tank_stock else None

#     same_fish_tanks = []
#     if fish:
#         same_fish_tanks = (
#             db.session.query(Tank)
#             .join(TankStock, Tank.tank_id == TankStock.tank_id)
#             .filter(
#                 TankStock.type_id == fish.type_id,
#                 Tank.tank_code != tank_code
#             )
#             .all()
#         )

#     return api_response(data={
#         "tank": {
#             "tank_code": tank.tank_code,
#             "name": tank.name,
#             "description": tank.description,
#         },
#         "fish": fish.to_dict() if fish else None,
#         "same_fish_tanks": [
#             {"tank_code": t.tank_code, "name": t.name} for t in same_fish_tanks
#         ]
#     })