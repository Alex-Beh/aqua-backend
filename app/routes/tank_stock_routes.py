from flask import Blueprint, request
from sqlalchemy import or_
from app.models import TankStock, StockAdjustment
from app import db
from datetime import datetime
from app.models.site import Site
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
# ✅ List all tank stock records, with optional filtering by tankId or fishTypeId
@stock_bp.route("/paging", methods=["GET"])
def get_list_stock_paged():
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)

    # Filter parameters
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)

    # Sorting parameters
    sort_field = request.args.get("sortField", "tank_name")
    sort_order = request.args.get("sortOrder", "asc")

    valid_sort_fields = ["tank_name", "common_name"]
    if sort_field not in valid_sort_fields:
        return api_response(f"Invalid sortField: {sort_field}", status=400)

    # Base query with eager loading
    q = TankStock.query.options(
        joinedload(TankStock.tank),
        joinedload(TankStock.fish_type)
    )

    # Apply filters
    if tank_id:
        q = q.filter(TankStock.tank_id == tank_id).join(FishType)
    elif fish_type_id:
        q = q.filter(TankStock.fish_type_id == fish_type_id).join(Tank)
    else:
        q = q.join(Tank).join(FishType)

    # Sorting using explicit mapping
    sort_mapping = {
        "tank_name": Tank.tank_name,
        "common_name": FishType.common_name
    }
    sort_column = sort_mapping.get(sort_field, Tank.tank_name)
    q = q.order_by(sort_column.desc() if sort_order == "desc" else sort_column)

    # Apply pagination without passing sort field
    paginated_data = paginate_response(q, page, size, sort_order)

    return api_response("Tank stock retrieved successfully", data=paginated_data)

# ✅ List all tank stock records, with optional filtering by tankId or fishTypeId
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

# ✅ Get a specific tank+fish_type stock record (read-only)
@stock_bp.route("/<int:tank_id>/<int:fish_type_id>", methods=["GET"])
def get_stock(tank_id, fish_type_id):
    stock = TankStock.query.filter_by(tank_id=tank_id, fish_type_id=fish_type_id).first()
    if not stock:
        return api_response("Tank stock not found", status=404)
    return api_response("Tank stock retrieved", data=stock.to_dict())

# ✅ List low-stock entries under a threshold (e.g., below 10)
@stock_bp.route("/low-stock", methods=["GET"])
def low_stock():
    threshold = request.args.get("threshold", default=10, type=int)
    low_stocks = TankStock.query.filter(TankStock.quantity < threshold).join(Tank).join(FishType).order_by(Tank.tank_name).all()
    
    result = [ts.to_dict() for ts in low_stocks]
    return api_response(f"Stocks with quantity below {threshold}", data=result)

# ✅ Get the total quantity of a specific fish type across all tanks
@stock_bp.route("/total-quantity/<int:fish_type_id>", methods=["GET"])
def get_total_quantity(fish_type_id):
    # Query the total quantity of the specific fish type across all tanks
    total_quantity = db.session.query(db.func.sum(TankStock.quantity)).filter_by(fish_type_id=fish_type_id).scalar()

    if total_quantity is None:
        return api_response("No records found for the given fish type", status=404)
    
    # Query to get the details of the fish type (e.g., common name, scientific name)
    fish_type = FishType.query.get(fish_type_id)
    if not fish_type:
        return api_response("Fish type not found", status_code=404)

    # Return the total quantity along with the fish type details
    return api_response(
        f"Total quantity of fish type {fish_type.common_name} : {total_quantity}",
        data={"totalQuantity": total_quantity, "fishType": fish_type.to_dict()}
    )

# Get total quantity for each tank, including a breakdown by fish type
@stock_bp.route("/summary", methods=["GET"])
def get_total_quantity_per_tank():
    siteId = request.args.get("siteId", type=int)

    # Base query to get total quantities
    query = db.session.query(
        TankStock.tank_id,
        db.func.sum(TankStock.quantity).label("total_quantity")
    ).group_by(TankStock.tank_id).join(Tank)

    # Apply site filter if siteId is provided
    if siteId and siteId > 0:
        query = query.filter(Tank.site_id == siteId)

    total_quantities = query.all()

    tanks = {tank.tank_id: tank for tank in Tank.query.filter(Tank.tank_id.in_([t[0] for t in total_quantities])).all()}

    result = []
    for tank_id, total_quantity in total_quantities:
        tank = tanks.get(tank_id)
        if tank:
            result.append(build_tank_details(tank_id, total_quantity, tank))

    result.sort(key=lambda x: x['tankName'])

    return api_response("Total quantities per tank with fish type breakdown retrieved successfully", data=result)

@stock_bp.route("/top-by-quantity", methods=["GET"])
def get_top_tanks_by_quantity():
    limit = request.args.get("limit", default=5, type=int)
    siteId = request.args.get("siteId", type=int)  # Get siteId from query parameters

    # Base query to get total quantities
    query = db.session.query(
        TankStock.tank_id,
        db.func.sum(TankStock.quantity).label("total_quantity")
    ).group_by(TankStock.tank_id) \
     .join(Tank) \
     .order_by(db.desc("total_quantity"))

    # Apply site filter if site_id is provided
    if siteId and siteId > 0:
        query = query.filter(Tank.site_id == siteId)

    total_quantities = query.limit(limit).all()

    tanks = {tank.tank_id: tank for tank in Tank.query.filter(Tank.tank_id.in_([t[0] for t in total_quantities])).all()}

    result = []
    for tank_id, total_quantity in total_quantities:
        tank = tanks.get(tank_id)
        if tank:
            result.append(build_tank_details(tank_id, total_quantity, tank))

    return api_response("Top tanks by fish inventory", data=result)

def build_tank_details(tank_id, total_quantity, tank_obj):
    # Query fish breakdown
    fish_quantities = db.session.query(
        TankStock.fish_type_id,
        db.func.sum(TankStock.quantity).label("fish_total_quantity")
    ).filter(TankStock.tank_id == tank_id) \
     .group_by(TankStock.fish_type_id) \
     .join(FishType).all()

    fish_details = []
    for fish_type_id, fish_total_quantity in fish_quantities:
        fish_type = FishType.query.get(fish_type_id)
        if fish_type:
            fish_details.append({
                "fishTypeId": fish_type_id,
                "commonName": fish_type.common_name,
                "scientificName": fish_type.scientific_name,
                "fishTotalQuantity": fish_total_quantity,
                "createdAt": fish_type.created_at.isoformat() if fish_type.created_at else None,
                "updatedAt": fish_type.updated_at.isoformat() if fish_type.updated_at else None,
            })

    capacity = max(tank_obj.capacity or 0, 1)
    filled_percentage = round((total_quantity / capacity) * 100, 2)

    return {
        "tankId": tank_obj.tank_id,
        "tankName": tank_obj.tank_name,
        "status": tank_obj.status,
        "totalTankCapacity": capacity,
        "totalFishCount": total_quantity,
        "tankFilledPercentage": filled_percentage,
        "fishTypeCount": len(fish_details),
        "fishDetails": fish_details
    }

# ✅ Get Site Distribution including Total Fish Count, Tank Count, and Fish Type Count
@stock_bp.route("/site-distribution", methods=["GET"])
def get_site_distribution():
    siteId = request.args.get("siteId", type=int)  # Get siteId from query parameters
    
    # Base query to get site information
    query = db.session.query(
        Tank.site_id,
        db.func.count(Tank.tank_id).label("tank_count"),
        db.func.count(FishType.type_id).label("fish_type_count"),
        db.func.sum(TankStock.quantity).label("total_fish_count")
    ).join(TankStock, TankStock.tank_id == Tank.tank_id, isouter=True) \
     .join(FishType, TankStock.fish_type_id == FishType.type_id, isouter=True) \
     .group_by(Tank.site_id)

    # Apply site filter if siteId is provided
    if siteId and siteId > 0:
        query = query.filter(Tank.site_id == siteId)

    site_distribution = query.all()

    # Get site details
    sites = {site.site_id: site for site in Site.query.filter(Site.site_id.in_([s[0] for s in site_distribution])).all()}

    result = []
    for site_id, tank_count, fish_type_count, total_fish_count in site_distribution:
        site = sites.get(site_id)
        if site:
            result.append({
                "siteId": site_id,
                "siteName": site.site_name,
                "tankCount": tank_count,
                "fishTypeCount": fish_type_count,
                "totalFishCount": total_fish_count if total_fish_count is not None else 0,  # Default to 0 if no fish
                "site": site.to_dict()  # Assuming the `Site` model has a `to_dict()` method
            })

    return api_response("Site Distribution Summary retrieved successfully", data=result)

def build_fish_inventory_query(site_id=None, search_text=None):
    query = db.session.query(
        FishType.type_id,
        FishType.common_name,
        FishType.type_code,
        FishType.scientific_name,
        db.func.count(TankStock.tank_id.distinct()).label("tank_count"),
        db.func.sum(TankStock.quantity).label("total_stock")
    ).join(TankStock, TankStock.fish_type_id == FishType.type_id)

    if site_id:
        query = query.join(Tank, Tank.tank_id == TankStock.tank_id).filter(Tank.site_id == site_id)

    if search_text:
        search_text = f"%{search_text}%"
        query = query.filter(
            or_(
                FishType.common_name.ilike(search_text),
                FishType.type_code.ilike(search_text),
                FishType.scientific_name.ilike(search_text)
            )
        )

    query = query.group_by(
        FishType.type_id,
        FishType.common_name,
        FishType.type_code,
        FishType.scientific_name
    )

    return query

@stock_bp.route("/fish-inventory", methods=["GET"])
def fish_inventory():
    site_id = request.args.get("siteId", type=int)
    search_text = request.args.get("searchText", type=str)

    query = build_fish_inventory_query(site_id, search_text)
    query = query.order_by(FishType.common_name)  # Sort by name

    fish_inventory = query.all()

    result = [
        {
            "typeId": fish[0],
            "typeCode": fish[2],
            "commonName": fish[1],
            "scientificName": fish[3],
            "totalTankCount": fish[4],
            "totalFishCount": fish[5]
        } for fish in fish_inventory
    ]

    return api_response("Fish Inventory retrieved successfully", data=result)

@stock_bp.route("/top-by-fish-inventory", methods=["GET"])
def top_by_fish_inventory():
    site_id = request.args.get("siteId", type=int)
    search_text = request.args.get("searchText", type=str)
    limit = request.args.get("limit", type=int, default=5)

    query = build_fish_inventory_query(site_id, search_text)
    query = query.order_by(db.desc("total_stock")).limit(limit)

    top_fish = query.all()

    result = [
        {
            "typeId": fish[0],
            "typeCode": fish[2],
            "commonName": fish[1],
            "scientificName": fish[3],
            "totalTankCount": fish[4],
            "totalFishCount": fish[5]
        } for fish in top_fish
    ]

    return api_response("Top Fish Inventory retrieved successfully", data=result)


@stock_bp.route("/fish-inventory/paging", methods=["GET"])
def fish_inventory_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    site_id = request.args.get('siteId', type=int)
    search_text = request.args.get("searchText", type=str)
    sort_field = request.args.get("sortField", "common_name")
    sort_order = request.args.get("sortOrder", "asc")

    valid_sort_fields = ["common_name", "type_code", "scientific_name"]
    if sort_field not in valid_sort_fields:
        return api_response(f"Invalid sortField: {sort_field}", status=400)

    query = build_fish_inventory_query(site_id, search_text)

    # Sorting
    sort_mapping = {
        "common_name": FishType.common_name,
        "type_code": FishType.type_code,
        "scientific_name": FishType.scientific_name
    }
    sort_column = sort_mapping[sort_field]
    query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column)

    # Pagination
    total_count = query.count()  # More accurate than separate raw count
    items = query.offset((page - 1) * size).limit(size).all()

    result = [
        {
            "typeId": fish[0],
            "typeCode": fish[2],
            "commonName": fish[1],
            "scientificName": fish[3],
            "totalTankCount": fish[4],
            "totalFishCount": fish[5]
        } for fish in items
    ]

    return api_response(
        "Fish Inventory retrieved successfully",
        data={
            "total": total_count,
            "page": page,
            "size": size,
            "items": result
        }
    )
