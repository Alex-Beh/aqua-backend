import math
from flask import Blueprint, request
from sqlalchemy.orm import selectinload

from datetime import datetime, timedelta

from flask_login import current_user

from app import db
from app.models import StockAdjustment, FishType
from app.models.tank import Tank
from app.models.tank_stock import TankStock
from app.models.stock_take import StockTake
from app.models.stock_take_item import StockTakeItem
from app.utils import api_response, validate_json, paginate_response
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy import or_

# ---------------------------------------------------------------------------
# Stock‑adjustment endpoints ------------------------------------------------
# ---------------------------------------------------------------------------
adjust_bp = Blueprint("adjust_bp",  __name__,
                      url_prefix="/api/stock-adjustments")

# # Apply login_required globally for all routes in this blueprint
# @tanks_bp.before_request
# @login_required
# def before_request():
#     pass


def get_performed_by():
    return current_user.name if current_user.is_authenticated else "Anonymous"


@adjust_bp.route("/", methods=["GET"])
def list_adjustments():
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get(
        "fishTypeId", type=int)  # Updated to fish_type_id
    transaction_type = request.args.get("transactionType")
    since = request.args.get("since")  # ISO‑8601 strings
    until = request.args.get("until")

    q = StockAdjustment.query
    if tank_id:
        q = q.filter_by(tank_id=tank_id)
    if fish_type_id:
        q = q.filter_by(fish_type_id=fish_type_id)
    if transaction_type:
        q = q.filter(StockAdjustment.transaction_type ==
                     transaction_type.capitalize())
    if since:
        q = q.filter(StockAdjustment.transaction_date >= since)
    if until:
        q = q.filter(StockAdjustment.transaction_date <= until)

    # If no date range is provided, set a default limit (e.g., 100 records)
    rows = q.order_by(StockAdjustment.transaction_date.desc()).limit(100).all(
    ) if not since and not until else q.order_by(StockAdjustment.transaction_date.desc()).all()

    return api_response("Stock adjustments retrieved successfully", data=[adj.to_dict_light() for adj in rows])


@adjust_bp.route("/paging", methods=["GET"])
def list_adjustments_paged():
    # ---------------- Pagination -------------------------------------------------
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 10, type=int)

    # ---------------- Sorting ----------------------------------------------------
    sort_field = request.args.get("sortField", "transaction_date")
    sort_order = request.args.get("sortOrder", "desc")

    # ---------------- Filters ----------------------------------------------------
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)
    transaction_type = request.args.get("transactionType", type=str)
    since = request.args.get("since")          # ISO string
    until = request.args.get("until")          # ISO string
    search_text = request.args.get("searchText", "", type=str).strip()

    # ---------------- Base query (no JOIN yet) -----------------------------------
    query = StockAdjustment.query

    if tank_id:
        query = query.filter_by(tank_id=tank_id)
    if fish_type_id:
        query = query.filter_by(fish_type_id=fish_type_id)
    if transaction_type:
        query = query.filter_by(transaction_type=transaction_type)
    # if since:
    #     query = query.filter(
    #         StockAdjustment.transaction_date >= dtparse(since))
    # if until:
    #     query = query.filter(
    #         StockAdjustment.transaction_date <= dtparse(until))

    # ---------------- Text search (requires JOIN) --------------------------------
    if search_text:
        like = f"%{search_text.lower()}%"
        query = (
            query.join(FishType)
                 .filter(
                     or_(
                         db.func.lower(FishType.common_name).like(like),
                         db.func.lower(FishType.type_code).like(like),
                         db.func.lower(FishType.scientific_name).like(like),
                     )
            )
        )

    # ---------------- Eager-load relationships to avoid N+1 ----------------------
    query = query.options(
        selectinload(StockAdjustment.tank)              # tank relationship
        # ← use Tank.<attr>, not "tank_id"
        .load_only(Tank.tank_id, Tank.tank_code),

        # fish-type relationship
        selectinload(StockAdjustment.fish_type)
        .load_only(
            FishType.type_id,
            FishType.type_code,
            FishType.common_name,
        ),
    )

    # ---------------- Apply sorting ---------------------------------------------
    # Map allowed sort fields to ORM columns; default to transaction_date
    sort_map = {
        "transaction_date": StockAdjustment.transaction_date,
        "recorded_at": getattr(StockAdjustment, "recorded_at", StockAdjustment.transaction_date),
        "transaction_type": StockAdjustment.transaction_type,
    }
    sort_col = sort_map.get(sort_field, StockAdjustment.transaction_date)
    if (sort_order or "").lower() == "asc":
        query = query.order_by(sort_col.asc(), StockAdjustment.stock_adjustment_id.asc())
    else:
        query = query.order_by(sort_col.desc(), StockAdjustment.stock_adjustment_id.desc())

    # ---------------- Offset/limit pagination ------------------------------------
    items = (
        query.limit(size)
             .offset((page - 1) * size)
             .all()
    )

    # total count (fast because subquery re-uses filters)
    total = (
        db.session.query(db.func.count())
        .select_from(query.subquery())
        .scalar()
    )
    total_pages = max(math.ceil(total / size), 1)

    # ---------------- Response ----------------------------------------------------
    return api_response(
        "Stock adjustments retrieved successfully",
        data={
            "items": [adj.to_dict_light() for adj in items],
            "page": page,
            "size": size,
            "total": total,                # total rows across all pages
            "totalPages": total_pages,     # explicit page count
            "hasNext": page < total_pages,
            "hasPrev": page > 1,
        },
    )


@adjust_bp.route("/<int:adjustment_id>", methods=["GET"])
def get_adjustment(adjustment_id):
    adj = StockAdjustment.query.get(adjustment_id)
    return api_response("Stock adjustment retrieved successfully", data=adj.to_dict())


@adjust_bp.route("", methods=["POST"])
def upsert_stock():
    print("upsert stock")
    data = request.get_json(force=True)
    transaction_type = data.get("transactionType")
    if not transaction_type:
        return api_response("Missing required field: transactionType", status_code=400)
    return _handle_stock_change(transaction_type.upper())


@adjust_bp.route("/add", methods=["POST"])
def add_fish():
    return _handle_stock_change("ADDITION")


@adjust_bp.route("/remove", methods=["POST"])
def remove_fish():
    return _handle_stock_change("REMOVAL")


@adjust_bp.route("/death", methods=["POST"])
def record_death():
    return _handle_stock_change("DEATH")


@adjust_bp.route("/transfer", methods=["POST"])
def transfer_fish():
    return _handle_stock_change("TRANSFER")


@adjust_bp.route("/stock-take/create", methods=["POST"])
def create_stock_take():
    return _handle_stock_take_creation()

# --------------------- Core Handler ---------------------


def _handle_stock_change(transaction_type: str):
    data = request.get_json(force=True)
    tank_id = data["tankId"]
    target_tank_id = data.get("targetTankId")
    fish_type_id = data["fishTypeId"]
    quantity_change = int(data["quantity"])
    notes = data.get("notes")
    reason = data.get("reason")

    try:
        # Step 1: Validate required fields
        required_fields = ["tankId", "fishTypeId", "quantity"]
        if transaction_type == "TRANSFER":
            required_fields.append("targetTankId")

        errors = validate_json(required_fields)
        if errors:
            return api_response("One or more validation errors occurred", errors=errors, status_code=400)

        if transaction_type == "TRANSFER" and tank_id == target_tank_id:
            return api_response("Source and target tanks cannot be the same", status_code=400)

        # ✅ Block zero quantity
        if quantity_change <= 0:
            return api_response("Quantity must be greater than 0", status_code=400)

        # Step 2: Check tank existence and status
        source_tank = Tank.query.filter_by(
            tank_id=tank_id, deleted_at=None).first()
        if not source_tank or source_tank.status.lower() != "active":
            return api_response(f"Source tank {tank_id} is not in use (inactive or deleted).", status_code=400)

        # Check if stock take is in progress
        if StockTake.is_stock_take_in_progress(tank_id):
            return api_response(f"Tank {tank_id} has an active stock take (Draft or Pending). Adjustment not allowed.", status_code=400)

        if target_tank_id:
            target_tank = Tank.query.filter_by(
                tank_id=target_tank_id, deleted_at=None).first()
            if not target_tank or target_tank.status.lower() != "active":
                return api_response(f"Target tank {target_tank_id} is not in use (inactive or deleted).", status_code=400)

            # CHECK the target tank
            if StockTake.is_stock_take_in_progress(target_tank_id):
                return api_response(f"Target tank {target_tank_id} has an active stock take (Draft or Pending). Adjustment not allowed.", status_code=400)

        # Step 3: Validate Fish Type
        fish_type = FishType.query.filter_by(
            type_id=fish_type_id, deleted_at=None).first()
        if not fish_type:
            return api_response(f"Fish Type {fish_type_id} does not exist or is deleted.", status_code=400)
        if not fish_type.is_active:
            return api_response(f"Fish Type {fish_type_id} is currently inactive.", status_code=400)

        # Step 4: Quantity Validation (before update)
        if transaction_type in {"REMOVAL", "DEATH", "TRANSFER"}:
            current_qty = get_current_quantity(tank_id, fish_type_id)
            if current_qty < quantity_change:
                return api_response(f"Not enough fish in tank {tank_id} to perform {transaction_type.lower()}.", status_code=400)

        # Step 5: Perform update
        if transaction_type == "TRANSFER":
            # Save before/after values for logging
            source_before = get_current_quantity(tank_id, fish_type_id)
            target_before = get_current_quantity(target_tank_id, fish_type_id)

            # Update both tanks
            source_ts, target_ts = update_tank_stock(
                tank_id, fish_type_id, quantity_change, transaction_type, target_tank_id
            )
            db.session.flush()

            # Step 4: Create adjustment logs (after update)
            create_stock_adjustment(
                transaction_type="TRANSFER",
                tank_id=tank_id,
                fish_type_id=fish_type_id,
                quantity_before=source_before,
                quantity_after=source_ts.quantity,
                reason=reason,
                notes=notes,
                target_tank_id=target_tank_id,
                quantity_change=quantity_change
            )

            ts = source_ts  # for response

        else:
            # Save before value for logging
            quantity_before = get_current_quantity(tank_id, fish_type_id)

            # Perform update
            ts = update_tank_stock(tank_id, fish_type_id,
                                   quantity_change, transaction_type)
            db.session.flush()

            # Step 4: Create adjustment log (after update)
            create_stock_adjustment(
                transaction_type=transaction_type,
                tank_id=tank_id,
                fish_type_id=fish_type_id,
                quantity_before=quantity_before,
                quantity_after=ts.quantity,
                reason=reason,
                notes=notes
            )

        # Step 5: Commit all changes
        db.session.commit()

    except (ValueError, IntegrityError) as e:
        db.session.rollback()
        return api_response("Stock adjustment failed", errors=str(e), status_code=400)
    except SQLAlchemyError as e:
        db.session.rollback()
        return api_response("Unexpected DB error", errors=str(e), status_code=500)

    messages = {
        "ADDITION": "Fish added to tank",
        "REMOVAL": "Fish removed from tank",
        "DEATH": "Fish loss recorded",
        "TRANSFER": "Fish transferred to another tank"
    }

    return api_response(
        messages.get(transaction_type, "Fish stock updated"),
        data={"tankId": ts.tank_id, "fishTypeId": ts.fish_type_id},
        status_code=201 if ts.quantity == quantity_change and transaction_type == "ADDITION" else 200
    )


def get_current_quantity(tank_id, fish_type_id):
    # Query to get the current quantity of a specific fish type in a tank
    tank_stock = TankStock.query.filter_by(
        tank_id=tank_id, fish_type_id=fish_type_id).first()
    return tank_stock.quantity if tank_stock else 0


def create_stock_adjustment(transaction_type, tank_id, fish_type_id, quantity_before, quantity_after, reason, notes, quantity_change=None, target_tank_id=None):
    now = db.func.current_timestamp()
    transaction_type_clean = transaction_type.capitalize()

    if transaction_type == "TRANSFER":
        if not target_tank_id:
            raise ValueError("Target tank ID is required for Transfer Action")

        # Get source and target tank info
        source_tank = Tank.query.get(tank_id)
        target_tank = Tank.query.get(target_tank_id)

        # Get the current quantity in the target tank before the transfer
        target_quantity_before = get_current_quantity(
            target_tank_id, fish_type_id) - quantity_change

        source_quantity_after = quantity_after  # This is from the source tank's update
        target_quantity_after = target_quantity_before + \
            quantity_change  # quantity_change is Orignal User Input

        # Add transfer-related notes for source and target tanks, with information at the front and separated by a comma
        updated_notes_source = f"(Transferred to tank {target_tank.tank_code} - {target_tank.tank_name}), {notes or ''}"
        updated_notes_target = f"(Transferred from tank {source_tank.tank_code} - {source_tank.tank_name}), {notes or ''}"

       # Create adjustment records for both source and target tanks
        adjustments = [
            StockAdjustment(
                transaction_type=transaction_type_clean,
                tank_id=tank_id,
                fish_type_id=fish_type_id,
                quantity_before=quantity_before,
                quantity_after=source_quantity_after,
                reason=reason,
                notes=updated_notes_source,
                recorded_by=get_performed_by(),
                recorded_at=now
            ),
            StockAdjustment(
                transaction_type=transaction_type_clean,
                tank_id=target_tank_id,
                fish_type_id=fish_type_id,
                quantity_before=target_quantity_before,
                quantity_after=target_quantity_after,
                reason=reason,
                notes=updated_notes_target,
                recorded_by=get_performed_by(),
                recorded_at=now
            )
        ]

        db.session.add_all(adjustments)

    elif transaction_type in {"ADDITION", "REMOVAL", "DEATH"}:
        if transaction_type in {"REMOVAL", "DEATH"} and quantity_after > quantity_before:
            raise ValueError(
                f"Quantity after cannot exceed before for {transaction_type}")
        db.session.add(
            StockAdjustment(
                transaction_type=transaction_type_clean,
                tank_id=tank_id,
                fish_type_id=fish_type_id,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                reason=reason,
                notes=notes,
                recorded_by=get_performed_by(),
                recorded_at=now
            )
        )
    else:
        raise ValueError("Invalid transaction type")


def update_tank_stock(tank_id, fish_type_id, quantity_change, transaction_type, target_tank_id=None):
    now = db.func.current_timestamp()

    if transaction_type == "TRANSFER":
        if tank_id == target_tank_id:
            raise ValueError("Source and target tank cannot be the same")

        # Update source tank (subtract quantity)
        source_ts = TankStock.query.get((tank_id, fish_type_id))
        if not source_ts or source_ts.quantity < quantity_change:
            raise ValueError(f"Not enough fish in tank {tank_id} to transfer.")
        source_ts.quantity -= quantity_change
        source_ts.last_updated = now
        db.session.flush()  # Flush to ensure the source tank is updated

        # Update or add target tank stock (add quantity)
        target_ts = TankStock.query.get((target_tank_id, fish_type_id))
        if target_ts:
            target_ts.quantity += quantity_change
            target_ts.last_updated = now
        else:
            target_ts = TankStock(
                tank_id=target_tank_id,
                fish_type_id=fish_type_id,
                quantity=quantity_change,
                last_updated=now
            )
            db.session.add(target_ts)

        return source_ts, target_ts

    ts = TankStock.query.get((tank_id, fish_type_id))

    if transaction_type == "ADDITION":
        if ts:
            ts.quantity += quantity_change
            ts.last_updated = now
        else:
            ts = TankStock(tank_id=tank_id, fish_type_id=fish_type_id,
                           quantity=quantity_change, last_updated=now)
            db.session.add(ts)

    elif transaction_type in {"REMOVAL", "DEATH"}:
        if not ts or ts.quantity < quantity_change:
            raise ValueError(
                f"Not enough fish in tank {tank_id} to perform {transaction_type.lower()}.")
        ts.quantity -= quantity_change
        ts.last_updated = now

    return ts


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


@adjust_bp.route("/stock-take/update/<int:stock_take_id>", methods=["PUT"])
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


@adjust_bp.route("/stock-take/create-and-approve", methods=["POST"])
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


@adjust_bp.route("/stock-take/approve/<int:stock_take_id>", methods=["PUT"])
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


@adjust_bp.route("/stock-take/reject/<int:stock_take_id>", methods=["PUT"])
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


@adjust_bp.route("/stock-take/cancel/<int:stock_take_id>", methods=["PUT"])
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


@adjust_bp.route("/stock-take/<int:stock_take_id>", methods=["GET"])
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


@adjust_bp.route("/stock-take/paging", methods=["GET"])
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


@adjust_bp.route("/stock-take", methods=["GET"])
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


@adjust_bp.route("/stock-take-count", methods=["GET"])
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

    except SQLAlchemyError as e:
        return api_response("Unexpected DB error", errors=str(e), status_code=500)
