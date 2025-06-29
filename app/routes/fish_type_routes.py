import io
from flask import Blueprint, request, jsonify, send_from_directory, current_app, send_file, abort
from flask_login import current_user, login_required
from app.models import FishType
from app import db
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from app.services.fish_type_service import FishTypeService
from app.utils import api_response, validate_json, paginate_response

# # Helper function for file upload
# def allowed_file(filename):
#     ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

static_bs = Blueprint('static_files', __name__)

# # Apply login_required globally for all routes in this blueprint
# @static_bs.before_request
# @login_required
# def before_request():
#     pass

def get_performed_by():
    return current_user.name if current_user.is_authenticated else "Anonymous"

@static_bs.route('/uploads/fish_images/<type_code>')
def serve_fish_image(type_code):
    fish = FishType.query.filter(FishType.type_code == type_code).first()
    if not fish.image_data:
        abort(404)
    return send_file(io.BytesIO(fish.image_data), mimetype=fish.image_mime_type)

bp = Blueprint('fish_types', __name__, url_prefix='/api/fish-types')

# API Routes
# Get a paginated list of fish types (optionally filtered by status)
# GET /api/fish-types/paging
@bp.route('/paging', methods=['GET'])
def get_fish_types_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    status = request.args.get('status')
    sort_field = request.args.get('sortField', 'type_code')
    sort_order = request.args.get('sortOrder', 'asc')

    paginated_data = FishTypeService.get_paginated(page, size, status, sort_field, sort_order)

    return api_response("Fish types retrieved successfully", data=paginated_data)

# GET /api/fish-types?status=active
@bp.route('/', methods=['GET'])
def get_all_fish_types():
    status = request.args.get('status')
    fish_types = FishTypeService.get_all(status=status)
    return api_response("Fish types retrieved", data=[ft.to_dict(include_image_data=True) for ft in fish_types])

# GET Dropdown /api/fish-types
@bp.route('/dropdown', methods=['GET'])
def get_all_fish_types_dropdwon():
    status = request.args.get('status')
    fish_types = FishTypeService.get_all(status=status)
    return api_response("Fish types retrieved", data=[ft.to_dict_dropdown() for ft in fish_types])

# GET /api/fish-types/<int:type_id>
@bp.route('/<int:type_id>', methods=['GET'])
def get_fish_type(type_id):
    fish_type = FishTypeService.get_by_id(type_id)
    if not fish_type or fish_type.deleted_at:
        return api_response("Fish type not found", status_code=404)
    return api_response("Fish type retrieved", data=fish_type.to_dict(include_image_data=True))

# POST /api/fish-types
@bp.route('', methods=['POST'])
def create_fish_type():
    data = request.form.to_dict()
    image_file = request.files.get('image')

    return FishTypeService.create(data, image_file=image_file, performed_by=get_performed_by())

# PUT /api/fish-types/<int:type_id>
@bp.route('/<int:type_id>', methods=['PUT'])
def update_fish_type(type_id):
    fish_type = FishTypeService.get_by_id(type_id)
    if not fish_type or fish_type.deleted_at:
        return api_response("Fish type not found", status_code=404)

    data = request.form.to_dict()
    image_file = request.files.get('image')

    return FishTypeService.update(fish_type, data, image_file=image_file, performed_by=get_performed_by())

@bp.route('/<int:type_id>', methods=['DELETE'])
def delete_fish_type(type_id):
    return FishTypeService.delete(type_id, performed_by=get_performed_by())
