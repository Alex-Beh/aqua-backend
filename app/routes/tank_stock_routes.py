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
@stock_bp.route("/total-quantity-per-tank", methods=["GET"])
def get_total_quantity_per_tank():
    # Query the total quantity for each tank (sum of quantities of all fish types in the tank)
    total_quantities = db.session.query(
        TankStock.tank_id,
        db.func.sum(TankStock.quantity).label("total_quantity")
    ).group_by(TankStock.tank_id).join(Tank).all()

    tanks = {tank.tank_id: tank for tank in Tank.query.filter(Tank.tank_id.in_([t[0] for t in total_quantities])).all()}

    # Prepare the result
    result = []
    for tank_id, total_quantity in total_quantities:
        tank = tanks.get(tank_id)
        if tank:
            # Now query each fish type's total quantity in this tank
            fish_quantities = db.session.query(
                TankStock.fish_type_id,
                db.func.sum(TankStock.quantity).label("fish_total_quantity")
            ).filter(TankStock.tank_id == tank_id) \
             .group_by(TankStock.fish_type_id) \
             .join(FishType).all()

            # Prepare the breakdown of fish types and their quantities
            fish_details = []
            for fish_type_id, fish_total_quantity in fish_quantities:
                fish_type = FishType.query.get(fish_type_id)
                if fish_type:
                    fish_details.append({
                        "fishTypeId": fish_type_id,
                        "fishTypeName": fish_type.common_name,  # Common name of the fish type
                        "scientificName": fish_type.scientific_name,  # Scientific name of the fish type
                        # "imageUrl": fish_type.image_url,  # Image URL for the fish type
                        "fishTotalQuantity": fish_total_quantity,  # Total quantity of this fish type in the tank
                        # "status": "Active" if fish_type.is_active else "Inactive",  # Status of the fish type (Active/Inactive)
                        "createdAt": fish_type.created_at.isoformat() if fish_type.created_at else None,  # Date when the fish type was created
                        "updatedAt": fish_type.updated_at.isoformat() if fish_type.updated_at else None,  # Date when the fish type was last updated
                    })

            result.append({
                "tankId": tank.tank_id,
                "tankName": tank.tank_name,
                "totalQuantity": total_quantity,
                "fishDetails": fish_details  # Include fish type breakdown for each tank
            })

    # Now, manually sort by tank name
    result.sort(key=lambda x: x['tankName'])

    return api_response("Total quantities per tank with fish type breakdown", data=result)
