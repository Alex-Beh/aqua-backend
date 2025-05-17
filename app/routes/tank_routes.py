"""tanks.py
Blueprint for Tank CRUD operations.

Register in app.py:
    from tanks import tanks_bp
    app.register_blueprint(tanks_bp)
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

from flask_login import current_user, login_required
from app.models.site import Site
from app.services.tank_service import TankService
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

# # Apply login_required globally for all routes in this blueprint
# @tanks_bp.before_request
# @login_required
# def before_request():
#     pass

def get_performed_by():
    return current_user.name if current_user.is_authenticated else "Anonymous"

# Get a paginated list of tanks (optionally filtered by status and siteId)
@tanks_bp.route('/paging', methods=['GET'])
def get_tanks_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    status_filter = request.args.get('status')
    site_id_filter = request.args.get('siteId', type=int)
    sort_field = request.args.get('sortField', 'tank_code')
    sort_order = request.args.get('sortOrder', 'asc')  

    paginated_data = TankService.get_paginated(page, size, status_filter, site_id_filter, sort_field, sort_order)
    
    return api_response("Tanks retrieved successfully", data=paginated_data)

@tanks_bp.route('/', methods=['GET'])
def get_all_tanks():
    status_filter = request.args.get('status')
    site_id_filter = request.args.get('siteId', type=int)

    tanks = TankService.get_all(status_filter, site_id_filter)

    return api_response("Tanks retrieved successfully", data=[tank.to_dict() for tank in tanks])

@tanks_bp.route('/dropdown', methods=['GET'])
def get_all_tanks_dropdown():
    status_filter = request.args.get('status')
    site_id_filter = request.args.get('siteId', type=int)

    tanks = TankService.get_all(status_filter, site_id_filter)

    return api_response("Tanks retrieved successfully", data=[tank.to_dict_dropdown() for tank in tanks])

@tanks_bp.route('/<int:tank_id>', methods=['GET'])
def get_tank(tank_id):
    tank = TankService.get_by_id(tank_id)
    if not tank:
        return api_response("Tank not found", status_code=404)
    return api_response("Tank retrieved successfully", data=tank.to_dict())

@tanks_bp.route('/tank-code/<string:tank_code>', methods=['GET'])
def get_tank_by_code(tank_code):
    tank = TankService.get_by_code(tank_code)
    if not tank:
        return api_response("Tank not found", status_code=404)
    return api_response("Tank retrieved successfully", data=tank.to_dict())

@tanks_bp.route("", methods=["POST"])
def create_tank():
    data = request.get_json()
    return TankService.create(data, performed_by=get_performed_by())

@tanks_bp.route('/<int:tank_id>', methods=['PUT'])
def update_tank(tank_id):
    data = request.get_json()
    return TankService.update(tank_id, data, performed_by=get_performed_by())

@tanks_bp.route('/<int:tank_id>', methods=['DELETE'])
def delete_tank(tank_id):
    return TankService.delete(tank_id, performed_by=get_performed_by())

@tanks_bp.route('/batch', methods=['POST'])
def create_tank_batch():
    data = request.get_json()
    return TankService.batch_create(data, performed_by=get_performed_by())