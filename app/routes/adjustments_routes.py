
from flask import Blueprint, request, jsonify
from datetime import datetime

from app import db
from app.models import StockAdjustment
from app.models.fish_type import FishType
from app.models.tank import Tank
from app.models.tank_stock import TankStock
from app.utils import api_response, validate_json, paginate_response
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# ---------------------------------------------------------------------------
# Stock‑adjustment endpoints ------------------------------------------------
# ---------------------------------------------------------------------------
adjust_bp  = Blueprint("adjust_bp",  __name__, url_prefix="/api/stock-adjustments")

# --------------------- Serialization ---------------------
def _serialize_stock(ts: TankStock) -> dict:
    return {
        "tankId": ts.tank_id,
        "fishTypeId": ts.fish_type_id,
        "quantity": ts.quantity,
        "lastUpdated": ts.last_updated.isoformat() if ts.last_updated else None,
    }

@adjust_bp.route("", methods=["GET"])
def list_adjustments():
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)  # Updated to fish_type_id
    since = request.args.get("since")  # ISO‑8601 strings
    until = request.args.get("until")

    q = StockAdjustment.query
    if tank_id:
        q = q.filter_by(tank_id=tank_id)
    if fish_type_id:
        q = q.filter_by(fish_type_id=fish_type_id)
    if since:
        q = q.filter(StockAdjustment.transaction_date >= since)
    if until:
        q = q.filter(StockAdjustment.transaction_date <= until)

    rows = q.order_by(StockAdjustment.transaction_date.desc()).all()
    return api_response("Stock adjustments retrieved successfully", data=[adj.to_dict() for adj in rows])

@adjust_bp.route("/<int:adjustment_id>", methods=["GET"])
def get_adjustment(adjustment_id):
    adj = StockAdjustment.query.get(adjustment_id)
    return api_response("Stock adjustment retrieved successfully", data=adj.to_dict())

@adjust_bp.route("", methods=["POST"])
def upsert_stock():
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
        if quantity_change == 0:
            return api_response("Quantity must be greater than 0", status_code=400)

        # Step 2: Check tank existence and status
        source_tank = Tank.query.filter_by(tank_id=tank_id, deleted_at=None).first()
        if not source_tank or source_tank.status.lower() != "active":
            return api_response(f"Source tank {tank_id} is not in use (inactive or deleted).", status_code=400)

        if target_tank_id:
            target_tank = Tank.query.filter_by(tank_id=target_tank_id, deleted_at=None).first()
            if not target_tank or target_tank.status.lower() != "active":
                return api_response(f"Target tank {target_tank_id} is not in use (inactive or deleted).", status_code=400)

        # Step 3: Validate Fish Type
        fish_type = FishType.query.filter_by(type_id=fish_type_id, deleted_at=None).first()
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
            ts = update_tank_stock(tank_id, fish_type_id, quantity_change, transaction_type)
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
    tank_stock = TankStock.query.filter_by(tank_id=tank_id, fish_type_id=fish_type_id).first()
    return tank_stock.quantity if tank_stock else 0

# --------------------- Adjustment Record ---------------------
def create_stock_adjustment(transaction_type, tank_id, fish_type_id, quantity_before, quantity_after, reason, notes, quantity_change=None, target_tank_id=None):
    now = datetime.utcnow()
    transaction_type_clean = transaction_type.capitalize()

    if transaction_type == "TRANSFER":
        if not target_tank_id:
            raise ValueError("Target tank ID is required for TRANSFER")

        # Get the current quantity in the target tank before the transfer
        target_quantity_before = get_current_quantity(target_tank_id, fish_type_id) - quantity_change

        source_quantity_after = quantity_after  # This is from the source tank's update
        target_quantity_after = target_quantity_before + quantity_change #quantity_change is Orignal User Input

       # Create adjustment records for both source and target tanks
        adjustments = [
            StockAdjustment(
                transaction_type=transaction_type_clean,
                tank_id=tank_id,
                fish_type_id=fish_type_id,
                quantity_before=quantity_before,
                quantity_after=source_quantity_after,
                reason=reason,
                notes=notes,
                recorded_at=now
            ),
            StockAdjustment(
                transaction_type=transaction_type_clean,
                tank_id=target_tank_id,
                fish_type_id=fish_type_id,
                quantity_before=target_quantity_before,
                quantity_after=target_quantity_after,
                reason=reason,
                notes=notes,
                recorded_at=now
            )
        ]

        db.session.add_all(adjustments)

    elif transaction_type == "ADDITION":
        db.session.add(
            StockAdjustment(
                transaction_type=transaction_type_clean,
                tank_id=tank_id,
                fish_type_id=fish_type_id,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                reason=reason,
                notes=notes,
                recorded_at=now
            )
        )

    elif transaction_type in {"REMOVAL", "DEATH"}:
        if quantity_after > quantity_before:
            raise ValueError(f"Quantity after cannot exceed before for {transaction_type}")
        db.session.add(
            StockAdjustment(
                transaction_type=transaction_type_clean,
                tank_id=tank_id,
                fish_type_id=fish_type_id,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                reason=reason,
                notes=notes,
                recorded_at=now
            )
        )
    else:
        raise ValueError("Invalid transaction type")

# --------------------- Stock Update ---------------------
def update_tank_stock(tank_id, fish_type_id, quantity_change, transaction_type, target_tank_id=None):
    now = datetime.utcnow()

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
            ts = TankStock(tank_id=tank_id, fish_type_id=fish_type_id, quantity=quantity_change, last_updated=now)
            db.session.add(ts)

    elif transaction_type in {"REMOVAL", "DEATH"}:
        if not ts or ts.quantity < quantity_change:
            raise ValueError(f"Not enough fish in tank {tank_id} to perform {transaction_type.lower()}.")
        ts.quantity -= quantity_change
        ts.last_updated = now

    return ts
