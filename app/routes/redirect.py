from flask import Blueprint, redirect, abort, current_app
from app import db
from app import config   # adjust if you use an app factory pattern
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
    """Return dummy tank and fish details for public QR view"""
    # Replace this section with real DB queries later
    dummy_data = {
        "tank": {
            "tank_code": tank_code,
            "name": "Tank 01",
            "description": "Front left tank for display fish"
        },
        "fish": {
            "type_id": 1,
            "type_code": "GUPPY-RED",
            "common_name": "Leopard snake skin",
            "scientific_name": "Poecilia reticulata",
            "image_url": "https://aqua-backend-xdbk.onrender.com/uploads/fish_images/FISH-0002"
        },
        "same_fish_tanks": [
            {"tank_code": "tank-02", "name": "Tank 02"},
            {"tank_code": "tank-03", "name": "Tank 03"}
        ]
    }
    return api_response("Public QR Tank retrieved successfully", data=dummy_data)

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