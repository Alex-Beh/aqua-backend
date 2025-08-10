import math
from flask import Blueprint, request
from sqlalchemy.orm import selectinload

from flask_login import current_user

from app import db
from app.models import StockAdjustment, FishType
from app.models.tank import Tank
from app.models.tank_stock import TankStock
from app.models.stock_take import StockTake
from app.utils import api_response, validate_json
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
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
            # make sure this helper exists
            "items": [adj.to_dict() for adj in items],
            "page":  page,
            "size":  size,
            "total": total_pages,
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


