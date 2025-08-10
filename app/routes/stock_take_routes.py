from flask import Blueprint, request
from flask_login import current_user
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app import db
from app.models import StockAdjustment, FishType
from app.models.tank import Tank
from app.models.tank_stock import TankStock
from app.models.stock_take import StockTake
from app.models.stock_take_item import StockTakeItem
from app.utils import api_response, paginate_response


stock_take_bp = Blueprint("stock_take_bp", __name__, url_prefix="/api/stock-take")


def get_performed_by():
    return current_user.name if current_user.is_authenticated else "Anonymous"


@stock_take_bp.route("/create", methods=["POST"])
def create_stock_take():
    return _handle_stock_take_creation()


def _handle_stock_take_creation():
    data = request.get_json(force=True)
    remarks = data.get("remarks")
    tank_id = data.get("tankId")
    fish_items = data.get("fishItems")
    status = data.get("status", "Pending").capitalize()

    if status not in ['Draft', 'Pending']:
        return api_response("Invalid status. Allowed values are 'Draft' or 'Pending'", status_code=400)

    if not tank_id:
        return api_response("Missing required field for Tank Id", status_code=400)

    if not fish_items or not isinstance(fish_items, list):
        return api_response("Fish Items should be a non-empty list", status_code=400)

    try:
        tank = Tank.query.get(tank_id)
        if not tank:
            return api_response("Tank not found", status_code=404)
        if tank.status.lower() != 'active':
            return api_response("Stock take can only be performed on active tanks", status_code=400)

        if StockTake.is_stock_take_in_progress(tank_id):
            return api_response("A stock take is already in progress for this tank (Draft or Pending status).", status_code=400)

        # Validate fish items
        valid_ids, id_to_name, expected_qty_map = extract_fish_stock_info(
            tank_id)
        errors = validate_fish_items_stock_take(
            fish_items, valid_ids, id_to_name)
        if errors:
            return api_response("There were errors with the fish items.", errors=errors, status_code=400)

        # Create StockTake
        now = db.func.current_timestamp()
        stock_take = StockTake(
            site_id=tank.site_id,
            tank_id=tank_id,
            remarks=remarks,
            status=status,
            initiate_by=get_performed_by(),
            initiate_at=now,
            created_by=get_performed_by(),
            created_at=now,
        )
        db.session.add(stock_take)
        db.session.flush()

        # Create items
        items = build_stock_take_items(
            stock_take.stock_take_id, fish_items, expected_qty_map)
        db.session.add_all(items)
        db.session.commit()

        return api_response("Stock take created successfully", data={"stockTakeId": stock_take.stock_take_id}, status_code=201)

    except SQLAlchemyError as e:
        db.session.rollback()
        return api_response("Unexpected DB error", errors=str(e), status_code=500)


@stock_take_bp.route("/update/<int:stock_take_id>", methods=["PUT"])
def update_stock_take(stock_take_id):
    data = request.get_json(force=True)
    remarks = data.get("remarks")
    fish_items = data.get("fishItems")
    status = data.get("status", "Pending").capitalize()

    if not fish_items or not isinstance(fish_items, list):
        return api_response("Fish Items should be a non-empty list", status_code=400)

    try:
        stock_take = StockTake.query.get(stock_take_id)
        if not stock_take:
            return api_response("Stock take not found", status_code=404)

        if stock_take.status not in ["Draft", "Pending"]:
            return api_response(f"Stock take with status '{stock_take.status}' cannot be updated", status_code=400)

        tank = Tank.query.get(stock_take.tank_id)
        if not tank or tank.status.lower() != "active":
            return api_response("Cannot update stock take for inactive or missing tank", status_code=400)

        # Re-validate fish items
        valid_ids, id_to_name, expected_qty_map = extract_fish_stock_info(
            tank.tank_id)
        errors = validate_fish_items_stock_take(
            fish_items, valid_ids, id_to_name)
        if errors:
            return api_response("There were errors with the fish items.", errors=errors, status_code=400)

        # Update main existing stock take
        stock_take.remarks = remarks
        stock_take.updated_by = get_performed_by()
        stock_take.updated_at = db.func.current_timestamp()
        stock_take.status = status

        current_user = get_performed_by()
        if stock_take.initiate_by != current_user:
            stock_take.initiate_by = current_user
            stock_take.initiate_at = db.func.current_timestamp()

        # Delete existing items and re-add
        StockTakeItem.query.filter_by(stock_take_id=stock_take_id).delete()

        new_items = build_stock_take_items(
            stock_take_id, fish_items, expected_qty_map)
        db.session.add_all(new_items)

        db.session.commit()
        return api_response("Stock take updated successfully")

    except SQLAlchemyError as e:
        db.session.rollback()
        return api_response("Unexpected DB error", errors=str(e), status_code=500)


@stock_take_bp.route("/create-and-approve", methods=["POST"])
def quick_create_and_approve_stock_take():
    data = request.get_json(force=True)

    # Reuse the creation logic (call the internal method)
    create_response, status_code = _handle_stock_take_creation()
    if status_code != 201:
        return create_response, status_code

    stock_take_id = create_response.get_json().get("data", {}).get("stockTakeId")
    if not stock_take_id:
        return api_response("Failed to retrieve new stock take ID", status_code=500)

    # Now immediately approve it
    review_comment = data.get("reviewComment", "Auto-approved")
    try:
        approve_stock_take_logic(stock_take_id, review_comment)
        return api_response("Stock take created and approved successfully", data={"stockTakeId": stock_take_id})
    except Exception as e:
        return api_response("Stock take created but approval failed", errors=str(e), status_code=500)


def get_tank_stock_list(tank_id=None, fish_type_id=None, site_id=None):
    q = TankStock.query.options(
        joinedload(TankStock.tank),
        joinedload(TankStock.fish_type)
    ).join(Tank).join(FishType)

    # Apply filters
    if tank_id and tank_id > 0:
        q = q.filter(TankStock.tank_id == tank_id)

    # Always apply consistent ordering
    q = q.order_by(Tank.tank_name, FishType.common_name)

    return [ts.to_dict() for ts in q.all()]


def extract_fish_stock_info(tank_id):
    """
    Get valid fish_type_ids, name mapping, and expected quantities from tank stock.
    """
    fish_stock_list = get_tank_stock_list(tank_id=tank_id)
    valid_ids = {item["fishTypeId"] for item in fish_stock_list}
    id_to_name = {item["fishTypeId"]: item["fishType"]
                  ["commonName"] for item in fish_stock_list}
    id_to_expected_qty = {item["fishTypeId"]: item["quantity"] for item in fish_stock_list}
    return valid_ids, id_to_name, id_to_expected_qty


def validate_fish_items_stock_take(fish_items, valid_fish_type_ids, fish_type_id_to_name):
    errors = {}
    for item in fish_items:
        fish_type_id = item.get("fishTypeId")
        counted_quantity = item.get("countedQuantity")
        item_errors = []

        if not fish_type_id:
            item_errors.append("Fish type ID is required.")
        elif fish_type_id not in valid_fish_type_ids:
            item_errors.append(
                "This fish type does not exist in this tank’s stock.")

        if counted_quantity is None or counted_quantity < 0:
            item_errors.append(
                "Counted quantity must be a non-negative integer.")

        if item_errors:
            label = fish_type_id_to_name.get(
                fish_type_id, f"Unknown Fish Type ({fish_type_id})")
            errors[label] = item_errors

    return errors


def build_stock_take_items(stock_take_id, fish_items, expected_quantity_map):
    """
    Converts raw fish_items into StockTakeItem instances.
    """
    return [
        StockTakeItem(
            stock_take_id=stock_take_id,
            fish_type_id=item["fishTypeId"],
            expected_quantity=expected_quantity_map.get(item["fishTypeId"], 0),
            counted_quantity=item["countedQuantity"]
        ) for item in fish_items
    ]

# Common function for fetching stock take and validating status


def get_stock_take_and_validate(stock_take_id, valid_statuses, action):
    stock_take = StockTake.query.get(stock_take_id)
    if not stock_take:
        raise ValueError("Stock take not found")

    if stock_take.status not in valid_statuses:
        raise ValueError(
            f"Stock take with status '{stock_take.status}' cannot be {action}")

    return stock_take

# Common logic for updating status


def update_stock_take_status(stock_take, status, review_comment):
    stock_take.status = status
    stock_take.review_comment = review_comment
    stock_take.updated_by = get_performed_by()
    stock_take.finalize_by = get_performed_by()
    stock_take.finalize_at = db.func.current_timestamp()
    db.session.commit()

# Approve endpoint


@stock_take_bp.route("/approve/<int:stock_take_id>", methods=["PUT"])
def approve_stock_take(stock_take_id):
    data = request.get_json(force=True)
    review_comment = data.get("reviewComment")

    try:
        approve_stock_take_logic(stock_take_id, review_comment)
        return api_response("Stock take approved successfully")
    except ValueError as e:
        return api_response(str(e), status_code=400)
    except SQLAlchemyError as e:
        db.session.rollback()
        return api_response("Unexpected DB error", errors=str(e), status_code=500)


def approve_stock_take_logic(stock_take_id: int, review_comment: str = None):
    """
    Core logic for approving a stock take. Can be reused in tests or other routes.
    Raises ValueError or SQLAlchemyError as needed.
    """
    stock_take = get_stock_take_and_validate(
        stock_take_id, ["Pending"], "approve")

    # Apply changes to stock + log adjustments
    apply_stock_take_to_stock(stock_take, review_comment)

    # Update status to 'Approved'
    update_stock_take_status(stock_take, "Approved", review_comment)

    return stock_take


def apply_stock_take_to_stock(stock_take, review_comment):
    for item in stock_take.items:
        tank_stock = TankStock.query.filter_by(
            tank_id=stock_take.tank_id,
            fish_type_id=item.fish_type_id
        ).first()

        # Calculate the change
        new_quantity = item.counted_quantity
        old_quantity = tank_stock.quantity if tank_stock else 0

        # Skip if no change
        if new_quantity == old_quantity:
            continue

        # Format reason and notes with initiate_at
        now = db.session.execute(db.func.current_timestamp()).scalar()
        now_str = now.strftime("%b %d, %Y %I:%M %p") if now else "Unknown"
        init_str = stock_take.initiate_at.strftime(
            "%b %d, %Y %I:%M %p") if stock_take.initiate_at else "Unknown"

        reason = f"Stock take adjustment (initiated on {init_str}, applied on {now_str})"
        notes = f"Review comment: {review_comment or 'None'}"

        # Create StockAdjustment record
        stock_adjustment = StockAdjustment(
            transaction_type="Stock Take",
            tank_id=stock_take.tank_id,
            fish_type_id=item.fish_type_id,
            quantity_before=old_quantity,
            quantity_after=new_quantity,
            reason=reason,
            notes=notes,
            recorded_by=get_performed_by(),
            recorded_at=now
        )
        db.session.add(stock_adjustment)
        db.session.flush()

        # Link the adjustment to the item
        item.adjustment_id = stock_adjustment.stock_adjustment_id

        # Update or insert tank stock
        if tank_stock:
            tank_stock.quantity = new_quantity
            tank_stock.last_updated = db.func.current_timestamp()
        else:
            db.session.add(TankStock(
                tank_id=item.tank_id,
                fish_type_id=item.fish_type_id,
                quantity=new_quantity
            ))

# Reject endpoint


@stock_take_bp.route("/reject/<int:stock_take_id>", methods=["PUT"])
def reject_stock_take(stock_take_id):
    data = request.get_json(force=True)
    review_comment = data.get("reviewComment")

    try:
        stock_take = get_stock_take_and_validate(
            stock_take_id, ["Pending"], "reject")
        update_stock_take_status(stock_take, "Rejected", review_comment)

        return api_response("Stock take rejected successfully")

    except ValueError as e:
        return api_response(str(e), status_code=400)  # Handle validation error
    except SQLAlchemyError as e:
        db.session.rollback()
        return api_response("Unexpected DB error", errors=str(e), status_code=500)

# Cancel endpoint


@stock_take_bp.route("/cancel/<int:stock_take_id>", methods=["PUT"])
def cancel_stock_take(stock_take_id):
    data = request.get_json(force=True)
    review_comment = data.get("reviewComment")

    try:
        stock_take = get_stock_take_and_validate(
            stock_take_id, ["Draft", "Pending"], "cancel")
        update_stock_take_status(stock_take, "Cancelled", review_comment)

        return api_response("Stock take cancelled successfully")

    except ValueError as e:
        return api_response(str(e), status_code=400)  # Handle validation error
    except SQLAlchemyError as e:
        db.session.rollback()
        return api_response("Unexpected DB error", errors=str(e), status_code=500)


@stock_take_bp.route("/<int:stock_take_id>", methods=["GET"])
def get_stock_take(stock_take_id):
    """
    Retrieve full details of a stock take by ID,
    including metadata and associated fish type items.
    """
    stock_take = StockTake.query.get(stock_take_id)
    if not stock_take:
        return api_response("Stock take not found", status_code=404)

    return api_response("Stock take retrieved", data={
        "stockTake": stock_take.to_dict(),
        "items": [item.to_dict() for item in stock_take.items]
    })


@stock_take_bp.route("/paging", methods=["GET"])
def list_stock_takes_paged():
    # Pagination
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)

    # Sorting
    sort_field = request.args.get("sortField", "initiate_at")
    sort_order = request.args.get("sortOrder", "desc")

    # Filters
    site_id = request.args.get("siteId", type=int)
    tank_id = request.args.get("tankId", type=int)
    status_param = request.args.get("status", type=str)
    since = request.args.get("since")
    until = request.args.get("until")
    search_text = request.args.get("searchText", "", type=str).strip().lower()

    # Start building query
    query = StockTake.query

    # Filter by foreign keys
    if site_id and site_id > 0:
        query = query.filter(StockTake.site_id == site_id)
    if tank_id and tank_id > 0:
        query = query.filter(StockTake.tank_id == tank_id)
    if status_param:
        status_list = [s.strip().capitalize() for s in status_param.split(",")]
        query = query.filter(StockTake.status.in_(status_list))
    if since:
        query = query.filter(StockTake.initiate_at >= since)
    if until:
        query = query.filter(StockTake.initiate_at <= until)

    # Optional text search in fish type fields
    if search_text:
        search_pattern = f"%{search_text}%"
        query = query.filter(
            db.or_(
                db.func.lower(StockTake.initiate_by).like(search_pattern),
                db.func.lower(StockTake.finalize_by).like(search_pattern),
                db.func.lower(Tank.tank_name).like(search_pattern),
                db.func.lower(Tank.tank_code).like(search_pattern)
            )
        )

    allowed_sort_fields = ["initiate_by", "initiate_at",
                           "finalize_by", "finalize_at", "status"]
    if sort_field not in allowed_sort_fields:
        sort_field = "initiate_at"

    # Avoid duplicate results when joining
    query = query.distinct()

    # Perform pagination
    paginated = paginate_response(
        query=query,
        page=page,
        size=size,
        model_class=StockTake,
        sort_field=sort_field,
        sort_order=sort_order
    )

    return api_response("Stock takes retrieved successfully", data=paginated)


@stock_take_bp.route("/", methods=["GET"])
def list_stock_takes():
    """
    List stock takes with optional filters:
    - siteId
    - tankId
    - status
    - since (initiateAt >=)
    - until (initiateAt <=)
    """
    site_id = request.args.get("siteId", type=int)
    tank_id = request.args.get("tankId", type=int)
    status_param = request.args.get("status")
    since = request.args.get("since")  # ISO format
    until = request.args.get("until")

    q = StockTake.query

    if site_id:
        q = q.filter_by(site_id=site_id)
    if tank_id:
        q = q.filter_by(tank_id=tank_id)
    if status_param:
        status_list = [s.strip().capitalize() for s in status_param.split(",")]
        q = q.filter(StockTake.status.in_(status_list))
    if since:
        q = q.filter(StockTake.initiate_at >= since)
    if until:
        q = q.filter(StockTake.initiate_at <= until)

    # Optional limit for default view
    rows = q.order_by(StockTake.initiate_at.desc()).limit(100).all(
    ) if not since and not until else q.order_by(StockTake.initiate_at.desc()).all()

    return api_response("Stock takes retrieved", data=[r.to_dict() for r in rows])


@stock_take_bp.route("/count", methods=["GET"])
def stock_take_counts():
    """
    Return counts of stock takes by their status and the total count,
    with optional filters for tankId, siteId, and month/year.
    """
    site_id = request.args.get("siteId", type=int)
    tank_id = request.args.get("tankId", type=int)
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    since = request.args.get("since")
    until = request.args.get("until")

    try:
        if since:
            since = datetime.strptime(since, "%Y-%m-%d")
        if until:
            until = datetime.strptime(until, "%Y-%m-%d") + timedelta(days=1)

        # Start query on StockTake model
        q = StockTake.query

        # Apply filters
        if site_id:
            q = q.filter_by(site_id=site_id)
        if tank_id:
            q = q.filter_by(tank_id=tank_id)
        if month and year:
            q = q.filter(db.extract('month', StockTake.initiate_at) == month,
                         db.extract('year', StockTake.initiate_at) == year)

        # Apply date range filter (since and until)
        if since:
            q = q.filter(StockTake.initiate_at >= since)
        if until:
            q = q.filter(StockTake.initiate_at < until)

        # Count the number of stock takes for each status
        draft_count = q.filter_by(status="Draft").count()
        pending_count = q.filter_by(status="Pending").count()
        approved_count = q.filter_by(status="Approved").count()
        rejected_count = q.filter_by(status="Rejected").count()
        canceled_count = q.filter_by(status="Cancelled").count()

        # Total count of stock takes
        total_count = q.count()

        return api_response("Stock take counts retrieved successfully", data={
            "draftCount": draft_count,
            "pendingCount": pending_count,
            "approvedCount": approved_count,
            "rejectedCount": rejected_count,
            "cancelledCount": canceled_count,
            "totalCount": total_count
        })
