from flask import Blueprint, request
from app.models import TankStock, StockAdjustment
from app import db
from datetime import datetime
from app.utils import api_response
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

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
@stock_bp.route("", methods=["GET"])
def list_stock():
    tank_id = request.args.get("tankId", type=int)
    fish_type_id = request.args.get("fishTypeId", type=int)
    q = TankStock.query
    if tank_id:
        q = q.filter_by(tank_id=tank_id)
    if fish_type_id:
        q = q.filter_by(fish_type_id=fish_type_id)
    stock_list = [_serialize_stock(ts) for ts in q.all()]
    return api_response("Tank stock retrieved successfully", data=stock_list)

@stock_bp.route("", methods=["POST"])
def upsert_stock():
    data = request.get_json(force=True)
    transaction_type = data.get("transactionType")
    if not transaction_type:
        return api_response("Missing required field: transactionType", status_code=400)
    return _handle_stock_change(transaction_type.upper())

@stock_bp.route("/add", methods=["POST"])
def add_fish():
    return _handle_stock_change("ADDITION")

@stock_bp.route("/remove", methods=["POST"])
def remove_fish():
    return _handle_stock_change("REMOVAL")

@stock_bp.route("/death", methods=["POST"])
def record_death():
    return _handle_stock_change("DEATH")

@stock_bp.route("/transfer", methods=["POST"])
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

    try:
        if transaction_type == "TRANSFER" and tank_id == target_tank_id:
            return api_response("Source and target tanks cannot be the same", status_code=400)

        ts = TankStock.query.get((tank_id, fish_type_id))
        quantity_before = ts.quantity if ts else 0

        # Perform stock operation
        if transaction_type == "TRANSFER":
            source_ts, target_ts = update_tank_stock(
                tank_id, fish_type_id, quantity_change, transaction_type, target_tank_id
            )
            db.session.flush()  # Ensure new records have IDs for adjustment logs
            create_stock_adjustment(
                transaction_type, tank_id, fish_type_id,
                quantity_before, source_ts.quantity,
                notes, target_tank_id
            )
            ts = source_ts
        else:
            ts = update_tank_stock(tank_id, fish_type_id, quantity_change, transaction_type)
            db.session.flush()
            create_stock_adjustment(
                transaction_type, tank_id, fish_type_id,
                quantity_before, ts.quantity,
                notes
            )

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
        status_code=201 if quantity_before == 0 and transaction_type == "ADDITION" else 200
    )

# --------------------- Adjustment Record ---------------------
def create_stock_adjustment(transaction_type, tank_id, fish_type_id, quantity_before, quantity_after, notes, target_tank_id=None):
    now = datetime.utcnow()

    if transaction_type == "TRANSFER":
        if not target_tank_id:
            raise ValueError("Target tank ID is required for TRANSFER")

        db.session.add_all([
            StockAdjustment(
                transaction_type="OUT",
                source_tank_id=tank_id,
                target_tank_id=target_tank_id,
                fish_type_id=fish_type_id,
                quantity_before=quantity_before,
                quantity_after=quantity_before - (quantity_after or 0),
                reason=transaction_type,
                notes=notes,
                recorded_at=now
            ),
            StockAdjustment(
                transaction_type="IN",
                source_tank_id=tank_id,
                target_tank_id=target_tank_id,
                fish_type_id=fish_type_id,
                quantity_before=0,  # Optional: query existing target tank quantity
                quantity_after=quantity_after,
                reason=transaction_type,
                notes=notes,
                recorded_at=now
            )
        ])

    elif transaction_type == "ADDITION":
        db.session.add(
            StockAdjustment(
                transaction_type="IN",
                source_tank_id=tank_id,
                fish_type_id=fish_type_id,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                reason=transaction_type,
                notes=notes,
                recorded_at=now
            )
        )

    elif transaction_type in {"REMOVAL", "DEATH"}:
        if quantity_after > quantity_before:
            raise ValueError(f"Quantity after cannot exceed before for {transaction_type}")
        db.session.add(
            StockAdjustment(
                transaction_type="OUT",
                source_tank_id=tank_id,
                fish_type_id=fish_type_id,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                reason=transaction_type,
                notes=notes,
                recorded_at=now
            )
        )
    else:
        raise ValueError("Invalid transaction type")

# --------------------- Stock Update ---------------------
def update_tank_stock(tank_id, fish_type_id, quantity_change, transaction_type, target_tank_id=None):
    now = datetime.utcnow()

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

    elif transaction_type == "TRANSFER":
        if not ts or ts.quantity < quantity_change:
            raise ValueError(f"Not enough fish in tank {tank_id} to transfer.")
        ts.quantity -= quantity_change
        ts.last_updated = now

        target_ts = TankStock.query.get((target_tank_id, fish_type_id))
        if target_ts:
            target_ts.quantity += quantity_change
            target_ts.last_updated = now
        else:
            target_ts = TankStock(tank_id=target_tank_id, fish_type_id=fish_type_id, quantity=quantity_change, last_updated=now)
            db.session.add(target_ts)

        return ts, target_ts

    return ts
