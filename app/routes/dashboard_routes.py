"""dashboard.py
Blueprint for dashboard-related analytics and summary endpoints.

Register in app.py:
    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

from flask_login import current_user, login_required
from app.models.site import Site
from app.services.tank_service import TankService
from app.services.tank_stock_service import TankStockService
from app.utils import api_response, validate_json, paginate_response

from app import db
from app.models import Tank

# ---------------------------------------------------------------------------
# Dashboard endpoints ------------------------------------------------------
# ---------------------------------------------------------------------------
dashboard_bp = Blueprint("dashboard_bp", __name__, url_prefix="/api/dashboard")

# # Apply login_required globally for all routes in this blueprint
# @tanks_bp.before_request
# @login_required
# def before_request():
#     pass

@dashboard_bp.route("/summary", methods=["GET"])
def dashboard_summary():
    site_id = request.args.get("siteId", type=int)
    summary_data = TankStockService.get_fish_summary(site_id, detailed=True)
    return api_response("Dashboard Summary", data=summary_data)


@dashboard_bp.route("/top-by-quantity", methods=["GET"])
def get_top_tanks_by_quantity():
    limit = request.args.get("limit", default=5, type=int)
    site_id = request.args.get("siteId", type=int)

    top_tanks = TankStockService.get_top_tanks_by_quantity(limit, site_id)

    result = []
    for tank_id, total_quantity in top_tanks:
        tank = Tank.query.get(tank_id)
        if tank:
            result.append(TankStockService.build_tank_details(tank_id, total_quantity, tank, include_fish_details=False))

    return api_response("Top tanks by fish inventory", data=result)


@dashboard_bp.route("/site-distribution", methods=["GET"])
def get_site_distribution():
    site_id = request.args.get("siteId", type=int)

    site_distribution = TankStockService.get_site_distribution(site_id)

    result = []
    for site_id, tank_count, fish_type_count, total_fish_count in site_distribution:
        site = Site.query.get(site_id)
        if site:
            result.append({
                "siteId": site_id,
                "siteName": site.site_name,
                "tankCount": tank_count,
                "fishTypeCount": fish_type_count,
                "totalFishCount": total_fish_count or 0,
                "site": site.to_dict()
            })

    # Add dummy site if no result found
    if not result:
        fake_site = Site.query.first()
        if fake_site:
            result.append({
                "siteId": fake_site.id,
                "siteName": fake_site.site_name + " (Dummy)",
                "tankCount": 1,
                "fishTypeCount": 1,
                "totalFishCount": 100,
                "site": fake_site.to_dict()
            })
        else:
            result.append({
                "siteId": 0,
                "siteName": "Dummy Site",
                "tankCount": 1,
                "fishTypeCount": 1,
                "totalFishCount": 100,
                "site": {}
            })

    return api_response("Site Distribution Summary retrieved successfully", data=result)

@dashboard_bp.route("/top-by-fish-inventory", methods=["GET"])
def top_by_fish_inventory():
    site_id = request.args.get("siteId", type=int)
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)
    search_text = request.args.get("searchText", type=str)
    limit = request.args.get("limit", type=int, default=5)

    if not limit or limit < 5:
        limit = 5

    query = TankStockService.build_fish_inventory_query(site_id, tank_id, fish_type_id, search_text)
    query = query.order_by(db.desc("total_stock")).limit(limit)

    top_fish = query.all()

    result = [
        {
            "typeId": fish[0],
            "commonName": fish[1],
            "typeCode": fish[2],
            "scientificName": fish[3],
            "totalTankCount": fish[4],
            "totalFishCount": fish[5]
        } for fish in top_fish
    ]

    return api_response("Top Fish Inventory retrieved successfully", data=result)