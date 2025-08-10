from flask import Blueprint, request
from app.services.tank_stock_service import TankStockService
from app.utils import api_response

stock_bp = Blueprint("stock_bp", __name__, url_prefix="/api/tank-stock")

# # Apply login_required globally for all routes in this blueprint
# @stock_bp.before_request
# @login_required
# def before_request():
#     pass

# --------------------- Endpoints ---------------------
# List all tank stock records, with optional filtering by tankId or fishTypeId
@stock_bp.route("/paging", methods=["GET"])
def get_list_stock_paged():
    # Pagination
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)

    # Sorting
    sort_field = request.args.get("sortField", "tank_name")
    sort_order = request.args.get("sortOrder", "asc")

    # Filters
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)
    site_id = request.args.get("siteId", type=int)
    search_text = request.args.get("searchText", "", type=str).strip()

    paginated_data = TankStockService.get_paged_tank_stock(
        page, size, sort_field, sort_order, tank_id, fish_type_id, site_id, search_text
    )

    return api_response("Tank stock retrieved successfully", data=paginated_data)

# List all tank stock records, with optional filtering by tankId or fishTypeId
@stock_bp.route("/", methods=["GET"])
def list_stock():
    tank_id      = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)
    site_id      = request.args.get("siteId", type=int)
    search_text  = request.args.get("searchText", "", type=str).strip()

    query = TankStockService.get_all_tank_stock(
        tank_id, fish_type_id, site_id, search_text
    )
    stock_list = query.all()

    # --- Python-side sort by tank_name then fish common_name ---
    stock_list.sort(
        key=lambda ts: (
            ts.tank.tank_name.lower()  if ts.tank and ts.tank.tank_name else "",
            ts.fish_type.common_name.lower() if ts.fish_type else "",
        )
    )

    return api_response(
        "Tank stock retrieved successfully",
        data=[ts.to_dict_light() for ts in stock_list],
    )

# Get a specific tank+fish_type stock record (read-only)
@stock_bp.route("/<int:tank_id>/<int:fish_type_id>", methods=["GET"])
def get_stock(tank_id, fish_type_id):
    stock = TankStockService.get_all_tank_stock(tank_id=tank_id, fish_type_id=fish_type_id)
    if not stock:
        return api_response("Tank stock not found", status=404)
    return api_response("Tank stock retrieved", data=stock.to_dict())

# List low-stock entries under a threshold (e.g., below 10)
@stock_bp.route("/low-stock", methods=["GET"])
def low_stock():
    threshold = request.args.get("threshold", default=10, type=int)
    status = request.args.get("status", default=None, type=str)
    site_id = request.args.get("siteId", type=int)
    
    # Fetch low stock entries using the service method with additional filters
    low_stocks = TankStockService.get_low_stock(threshold=threshold, status=status, site_id=site_id)
    
    # Convert to dict and return response
    result = [ts.to_dict() for ts in low_stocks]
    return api_response(f"Stocks with quantity below {threshold}", data=result)


