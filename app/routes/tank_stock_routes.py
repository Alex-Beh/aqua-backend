from flask import Blueprint, request
from sqlalchemy import or_, cast, String, desc
from app.models import TankStock, StockAdjustment
from app import db
from datetime import datetime
from app.models.site import Site
from app.models.stock_take import StockTake
from app.models.stock_take_item import StockTakeItem
from app.utils import api_response, validate_json, paginate_response
from sqlalchemy.orm import joinedload
from app.models.tank import Tank
from app.models.fish_type import FishType
from sqlalchemy import func

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
    # Pagination
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)

    # Filters
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)
    site_id = request.args.get("siteId", type=int)
    search_text = request.args.get("searchText", "", type=str).strip()

    # Sorting
    sort_field = request.args.get("sortField", "tank_name")
    sort_order = request.args.get("sortOrder", "asc")

    valid_sort_fields = ["tank_name", "common_name", "quantity", "type_code"]
    if sort_field not in valid_sort_fields:
        sort_field = "tank_name"

    # Base query with joins
    q = TankStock.query.options(
        joinedload(TankStock.tank),
        joinedload(TankStock.fish_type)
    ).join(Tank).join(FishType)

    # Apply filters
    q = apply_tank_stock_filters(q, tank_id, fish_type_id, site_id, search_text)

    # Apply sorting
    sort_mapping = {
        "tank_name": Tank.tank_name,
        "common_name": FishType.common_name,
        "quantity": TankStock.quantity,
        "type_code": FishType.type_code
    }

    sort_column = sort_mapping.get(sort_field, Tank.tank_name)
    q = q.order_by(sort_column.desc() if sort_order == "desc" else sort_column)

    # Paginate results
    paginated_data = paginate_response(q, page, size, sort_order)

    return api_response("Tank stock retrieved successfully", data=paginated_data)


# ✅ List all tank stock records, with optional filtering by tankId or fishTypeId
@stock_bp.route("", methods=["GET"])
def list_stock():
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)
    site_id = request.args.get("siteId", type=int)

    stock_list = get_tank_stock_list(tank_id=tank_id, fish_type_id=fish_type_id, site_id=site_id)
    return api_response("Tank stock retrieved successfully", data=stock_list)

def get_tank_stock_list(tank_id=None, fish_type_id=None, site_id=None):
    q = TankStock.query.options(
        joinedload(TankStock.tank),
        joinedload(TankStock.fish_type)
    ).join(Tank).join(FishType)

    # Apply filters
    q = apply_tank_stock_filters(q, tank_id, fish_type_id, site_id)
    # Always apply consistent ordering
    q = q.order_by(Tank.tank_name, FishType.common_name)

    return [ts.to_dict() for ts in q.all()]

def apply_tank_stock_filters(q, tank_id=None, fish_type_id=None, site_id=None, search_text=""):
    if tank_id and tank_id > 0:
        q = q.filter(TankStock.tank_id == tank_id)
    if fish_type_id and fish_type_id > 0:
        q = q.filter(TankStock.fish_type_id == fish_type_id)
    if site_id and site_id > 0:
        q = q.filter(Tank.site_id == site_id)
    if search_text:
        search_lower = f"%{search_text.lower()}%"

        q = q.filter(
            db.or_(
                db.func.lower(Tank.tank_name).like(search_lower),
                db.func.lower(FishType.common_name).like(search_lower),
                db.func.lower(FishType.type_code).like(search_lower),
                cast(TankStock.quantity, String).like(search_lower)
            )
        )
    return q

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

@stock_bp.route("/dashboard/top-by-quantity", methods=["GET"])
def get_top_tanks_by_quantity():
    limit = request.args.get("limit", default=5, type=int)
    siteId = request.args.get("siteId", type=int)  # Get siteId from query parameters

    if(limit < 5):
        limit = 5
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
@stock_bp.route("/dashboard/site-distribution", methods=["GET"])
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

def build_fish_inventory_query(site_id=None, tank_id=None, fish_type_id=None, search_text=None):
    query = db.session.query(
        FishType.type_id,
        FishType.common_name,
        FishType.type_code,
        FishType.scientific_name,
        db.func.count(TankStock.tank_id.distinct()).label("tank_count"),
        db.func.sum(TankStock.quantity).label("total_stock")
    ).join(TankStock, TankStock.fish_type_id == FishType.type_id)

    if tank_id and tank_id > 0:
        query = query.filter(TankStock.tank_id == tank_id)

    if fish_type_id and fish_type_id > 0:
        query = query.filter(TankStock.fish_type_id == fish_type_id)

    if site_id and site_id > 0:
        query = query.join(Tank, Tank.tank_id == TankStock.tank_id).filter(Tank.site_id == site_id)

    if search_text:
        search_lower = f"%{search_text.lower()}%"
        query = query.filter(
            db.or_(
                db.func.lower(FishType.common_name).like(search_lower),
                db.func.lower(FishType.type_code).like(search_lower),
                db.func.lower(FishType.scientific_name).like(search_lower)
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
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)
    search_text = request.args.get("searchText", type=str)

    query = build_fish_inventory_query(site_id, tank_id, fish_type_id, search_text)
    query = query.order_by(FishType.common_name)  # Sort by name

    fish_inventory = query.all()

    result = [
        {
            "typeId": fish[0],
            "commonName": fish[1],
            "typeCode": fish[2],
            "scientificName": fish[3],
            "totalTankCount": fish[4],
            "totalFishCount": fish[5]
        } for fish in fish_inventory
    ]

    return api_response("Fish Inventory retrieved successfully", data=result)

@stock_bp.route("/dashboard/top-by-fish-inventory", methods=["GET"])
def top_by_fish_inventory():
    site_id = request.args.get("siteId", type=int)
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)

    search_text = request.args.get("searchText", type=str)
    limit = request.args.get("limit", type=int, default=5)

    if not limit or limit < 5:
        limit = 5

    query = build_fish_inventory_query(site_id, tank_id, fish_type_id, search_text)
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


@stock_bp.route("/fish-inventory/paging", methods=["GET"])
def fish_inventory_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    site_id = request.args.get('siteId', type=int)
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)
    search_text = request.args.get("searchText", type=str)
    sort_field = request.args.get("sortField", "common_name")
    sort_order = request.args.get("sortOrder", "asc")

    valid_sort_fields = ["common_name", "type_code", "scientific_name"]
    if sort_field not in valid_sort_fields:
        sort_field = "common_name"

    query = build_fish_inventory_query(site_id, tank_id, fish_type_id, search_text)

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
            "commonName": fish[1],
            "typeCode": fish[2],
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

def get_fish_stats(site_id=None):
    query = db.session.query(db.func.sum(TankStock.quantity))
    tank_query = db.session.query(db.func.count(db.distinct(TankStock.tank_id)))

    if site_id and site_id > 0:
        query = query.join(Tank, Tank.tank_id == TankStock.tank_id).filter(Tank.site_id == site_id)
        tank_query = tank_query.join(Tank, Tank.tank_id == TankStock.tank_id).filter(Tank.site_id == site_id)

    total_fish = query.scalar() or 0
    tank_count = tank_query.scalar() or 0

    return total_fish, tank_count


def get_active_tank_count(site_id=None):
    query = db.session.query(db.func.count(Tank.tank_id)).filter(db.func.lower(Tank.status) == "active")

    if site_id and site_id > 0:
        query = query.filter(Tank.site_id == site_id)

    return query.scalar() or 0

def get_fish_type_count(site_id=None):
    query = db.session.query(db.func.count(db.distinct(TankStock.fish_type_id))).join(Tank, Tank.tank_id == TankStock.tank_id)

    if site_id and site_id > 0:
        query = query.filter(Tank.site_id == site_id)

    return query.scalar() or 0

@stock_bp.route("/inventory/summary", methods=["GET"])
def inventory_summary():
    site_id = request.args.get("siteId", type=int)

    # Use the common method
    summary_data = get_fish_summary(site_id, detailed=False)

    return api_response("Inventory Summary", data=summary_data)

@stock_bp.route("/dashboard/summary", methods=["GET"])
def dashboard_summary():
    site_id = request.args.get("siteId", type=int)
    summary_data = get_fish_summary(site_id, detailed=True)
    return api_response("Dashboard Summary", data=summary_data)

def get_fish_summary(site_id=None, detailed=False):
    total_fish, tank_with_fish_count = get_fish_stats(site_id)
    active_tank_count = get_active_tank_count(site_id)
    fish_type_count = get_fish_type_count(site_id)

    summary = {
        "totalFishCount": total_fish,
        "tankWithFishCount": tank_with_fish_count,
        "activeTankCount": active_tank_count,
        "fishTypeCount": fish_type_count,
    }

    if detailed:
        # Only calculate this if detailed=True
        query = db.session.query(
            Tank.tank_id,
            db.func.sum(TankStock.quantity).label("total_quantity"),
            Tank.capacity
        ).join(TankStock, Tank.tank_id == TankStock.tank_id)

        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)

        query = query.filter(TankStock.quantity > 0)
        tank_data = query.group_by(Tank.tank_id, Tank.capacity).all()

        stocked_count = len(tank_data)
        total_tank_count = db.session.query(Tank).filter(
            Tank.site_id == site_id if site_id else True
        ).count()

        total_capacity = sum(tank.capacity or 0 for tank in tank_data)
        total_quantity = sum(tank.total_quantity or 0 for tank in tank_data)

        utilization = (stocked_count / total_tank_count * 100) if total_tank_count > 0 else 0
        capacity_utilization = (total_quantity / total_capacity * 100) if total_capacity > 0 else 0

        summary["tanksWithStock"] = {
            "count": stocked_count,
            "utilizationPercent": round(utilization, 1),
            "capacityUtilizationPercent": round(capacity_utilization, 1)
        }

        # Last Dashboard Summary Card (Stock Take)
        # Find the latest finalized stock take
        last_stock_take = db.session.query(StockTake).filter(
            StockTake.status == "Approved", 
            StockTake.finalize_at != None,
            (StockTake.site_id == site_id) if site_id is not None and site_id > 0 else True
        ).order_by(desc(StockTake.finalize_at)).first()

        if last_stock_take:
            item_count = db.session.query(StockTakeItem).filter_by(
                stock_take_id=last_stock_take.stock_take_id
            ).count()

            # Adding humanized "daysAgo"
            last_stock_take_date = last_stock_take.finalize_at
            summary["lastStockTake"] = {
                "date": last_stock_take_date.isoformat(),
                "daysAgo": humanize_days_ago(last_stock_take_date),
                "tankCount": 1,
                "itemCount": item_count,
                "status": last_stock_take.status,
                "remarks": last_stock_take.remarks
            }
        else:
            summary["lastStockTake"] = None

    return summary


def humanize_days_ago(dt):
    delta = (datetime.utcnow() - dt).days

    # Handle special cases
    if delta == 0:
        return "Today"
    elif delta == 1:
        return "Yesterday"
    elif delta < 7:
        return f"{delta} days ago"
    elif delta < 30:
        weeks = delta // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif delta < 365:
        months = delta // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = delta // 365
        return f"{years} year{'s' if years > 1 else ''} ago"


@stock_bp.route("/dashboard/total-fish-count", methods=["GET"])
def dashboard_total_fish_count():
    site_id = request.args.get("siteId", type=int)

    # Use the common method
    summary_data = get_fish_summary(site_id)

    return api_response("Total Fish Count", data=summary_data)


@stock_bp.route("/dashboard/total-active-tanks", methods=["GET"])
def active_tanks():
    site_id = request.args.get("siteId", type=int)

    # Use the dedicated method for active tank count
    active_tank_count = get_active_tank_count(site_id)

    return api_response("Total Active Tanks", data={
        "totalTankCount": active_tank_count,
        "label": "Available for fish storage"
    })

@stock_bp.route("/dashboard/tanks-with-stock", methods=["GET"])
def tanks_with_stock():
    site_id = request.args.get("siteId", type=int)

    query = db.session.query(
        Tank.tank_id,
        db.func.sum(TankStock.quantity).label("total_quantity"),
        Tank.capacity
    ).join(TankStock, Tank.tank_id == TankStock.tank_id)

    if site_id and site_id > 0:
        query = query.filter(Tank.site_id == site_id)

    query = query.filter(TankStock.quantity > 0)

    tank_data = query.group_by(Tank.tank_id, Tank.capacity).all()

    stocked_count = len(tank_data)
    total_tank_count = db.session.query(Tank).filter(
        Tank.site_id == site_id if site_id else True
    ).count()

    total_capacity = sum(tank.capacity or 0 for tank in tank_data)
    total_quantity = sum(tank.total_quantity or 0 for tank in tank_data)

    utilization = (
        (stocked_count / total_tank_count * 100) if total_tank_count > 0 else 0
    )

    capacity_utilization = (
        (total_quantity / total_capacity * 100) if total_capacity > 0 else 0
    )

    return api_response("Tanks With Stock", data={
        "count": stocked_count,
        "utilizationPercent": round(utilization, 1),
        "capacityUtilizationPercent": round(capacity_utilization, 1)
    })
