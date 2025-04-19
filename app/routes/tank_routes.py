"""tanks.py
Blueprint for Tank CRUD operations.

Register in app.py:
    from tanks import tanks_bp
    app.register_blueprint(tanks_bp)
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from app.utils import api_response, validate_json, paginate_response

from app import db
from app.models import Tank


def _serialize(tank: Tank) -> dict:
    """Return a dict representation using the model's to_dict method."""
    return tank.to_dict()


# ---------------------------------------------------------------------------
# Tank‑stock endpoints ------------------------------------------------------
# ---------------------------------------------------------------------------
tanks_bp = Blueprint("tanks_bp", __name__, url_prefix="/api/tanks")

# Get a paginated list of tanks (optionally filtered by status and siteId)
@tanks_bp.route('/paging', methods=['GET'])
def get_tanks_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    status_filter = request.args.get('status')
    # Ensure it's an integer if present
    site_id_filter = request.args.get('siteId', type=int)
    # Default sorting by tank_code
    sort_field = request.args.get('sortField', 'tank_code')
    sort_order = request.args.get('sortOrder', 'asc')  # Default ascending order

    query = Tank.query.filter(Tank.deleted_at.is_(None))

    # Apply status filter if present
    if status_filter:
        query = query.filter(Tank.status == status_filter.capitalize())

    # Apply site_id filter if present
    if site_id_filter:
        query = query.filter(Tank.site_id == site_id_filter)

    # Use paginate_response function to handle pagination
    paginated_data = paginate_response(
        query, page, size, Tank, sort_field, sort_order)

    return api_response("Tanks retrieved successfully", data=paginated_data)


@tanks_bp.route('', methods=['GET'])
def get_all_tanks():
    status_filter = request.args.get('status')
    # Ensure it's an integer if present
    site_id_filter = request.args.get('siteId', type=int)

    query = Tank.query.filter(Tank.deleted_at.is_(None))

    # Apply status filter if present
    if status_filter:
        query = query.filter(Tank.status == status_filter)

    # Apply site_id filter if present
    if site_id_filter:
        query = query.filter(Tank.site_id == site_id_filter)

    tanks = query.all()
    return api_response("Tanks retrieved successfully", data=[tank.to_dict() for tank in tanks])


@tanks_bp.route('/<int:tank_id>', methods=['GET'])
def get_tank(tank_id):
    tank = Tank.query.get(tank_id)
    if not tank or tank.deleted_at:
        return api_response("Tank not found", status_code=404)
    return api_response("Tank retrieved successfully", data=tank.to_dict())


@tanks_bp.route("", methods=["POST"])
def create_tank():
    data = request.get_json()

    validation_errors = Tank.validate_fields(data)
    if validation_errors:
        return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)

    # Generate auto tank code based on site_id
    try:
        tank_code = Tank.generate_auto_code(data['siteId'])
    except ValueError as e:
        return api_response(f"Error generating tank code: {str(e)}", status_code=400)

    status = data.get('status', 'Active')
    new_tank = Tank(
        site_id=data['siteId'],
        tank_name=data['tankName'],
        tank_code=tank_code.upper(),
        capacity=data.get('capacity'),
        status=status,
        created_at=datetime.utcnow()
    )
    db.session.add(new_tank)
    db.session.commit()
    return api_response("Tank created successfully", data=new_tank.to_dict(), status_code=201)


@tanks_bp.route('/<int:tank_id>', methods=['PUT'])
def update_tank(tank_id):
    tank = Tank.query.get(tank_id)
    if not tank or tank.deleted_at:
        return api_response("Tank not found", status_code=404)

    data = request.get_json()

    validation_errors = Tank.validate_fields(data, for_update=True)
    if validation_errors:
        return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)

    status = data.get('status', tank.status)

    tank.tank_name = data.get('tankName', tank.tank_name)
    tank.capacity = data.get('capacity', tank.capacity)
    tank.status = status
    tank.updated_at = datetime.utcnow()
    db.session.commit()

    return api_response("Tank updated successfully", data=tank.to_dict())


@tanks_bp.route('/<int:tank_id>', methods=['DELETE'])
def delete_tank(tank_id):
    tank = Tank.query.get(tank_id)
    if not tank or tank.deleted_at:
        return api_response("Tank not found", status_code=404)

    tank.soft_delete()
    db.session.commit()
    return api_response("Tank deleted successfully")
