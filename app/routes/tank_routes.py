from flask import Blueprint, request, jsonify
from app import db
from app.models.tank import Tank
from datetime import datetime
from app.utils import api_response, validate_json, paginate_response

bp = Blueprint('tanks', __name__, url_prefix='/api/tanks')

# Get a paginated list of tanks (optionally filtered by status and siteId)
@bp.route('/paging', methods=['GET'])
def get_tanks_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    status_filter = request.args.get('status')
    site_id_filter = request.args.get('siteId', type=int)  # Ensure it's an integer if present

    query = Tank.query.filter(Tank.deleted_at.is_(None))

    # Apply status filter if present
    if status_filter == 'active':
        query = query.filter(Tank.is_active.is_(True))
    elif status_filter == 'inactive':
        query = query.filter(Tank.is_active.is_(False))

    # Apply site_id filter if present
    if site_id_filter:
        query = query.filter(Tank.site_id == site_id_filter)

    # Use paginate_response function to handle pagination
    paginated_data = paginate_response(query, page, size, Tank)

    return api_response("Tanks retrieved successfully", data=paginated_data)

@bp.route('', methods=['GET'])
def get_all_tanks():
    status_filter = request.args.get('status')
    site_id_filter = request.args.get('siteId', type=int)  # Ensure it's an integer if present

    query = Tank.query.filter(Tank.deleted_at.is_(None))

    # Apply status filter if present
    if status_filter == 'active':
        query = query.filter(Tank.is_active.is_(True))
    elif status_filter == 'inactive':
        query = query.filter(Tank.is_active.is_(False))

    # Apply site_id filter if present
    if site_id_filter:
        query = query.filter(Tank.site_id == site_id_filter)

    tanks = query.all()
    return api_response("Tanks retrieved successfully", data=[tank.to_dict() for tank in tanks])

@bp.route('/<int:tank_id>', methods=['GET'])
def get_tank(tank_id):
    tank = Tank.query.get_or_404(tank_id)
    if not tank or tank.deleted_at:
        return api_response("Tank not found", status_code=404)
    return api_response("Tank retrieved successfully", data=tank.to_dict())

@bp.route('', methods=['POST'])
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
    
    new_tank = Tank(
        site_id=data['siteId'],
        tank_name=data['tankName'],
        tank_code=tank_code.upper(),
        capacity=data.get('capacity'),
        is_active=data.get('isActive', True),
        created_at=datetime.utcnow()
    )
    db.session.add(new_tank)
    db.session.commit()
    return api_response("Tank created successfully", data=new_tank.to_dict(), status_code=201)

@bp.route('/<int:tank_id>', methods=['PUT'])
def update_tank(tank_id):
    tank = Tank.query.get_or_404(tank_id)
    if not tank or tank.deleted_at:
        return api_response("Tank not found", status_code=404)
        
    data = request.get_json()
    tank.tank_name = data.get('tankName', tank.tank_name)
    tank.capacity = data.get('capacity', tank.capacity)
    tank.is_active = data.get('isActive', tank.is_active)
    tank.updated_at = datetime.utcnow()
    db.session.commit()

    return api_response("Tank updated successfully", data=tank.to_dict())

@bp.route('/<int:tank_id>', methods=['DELETE'])
def delete_tank(tank_id):
    tank = Tank.query.get(tank_id)
    if not tank or tank.deleted_at:
        return api_response("Tank not found", status_code=404)
    
    tank.soft_delete()
    db.session.commit()
    return api_response("Tank deleted successfully")
