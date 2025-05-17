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
@bp.route('', methods=['GET'])
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
    upload_folder = current_app.config['UPLOAD_FOLDER']

    return FishTypeService.create(data, image_file=image_file, upload_folder=upload_folder, performed_by=get_performed_by())

# PUT /api/fish-types/<int:type_id>
@bp.route('/<int:type_id>', methods=['PUT'])
def update_fish_type(type_id):
    fish_type = FishTypeService.get_by_id(type_id)
    if not fish_type or fish_type.deleted_at:
        return api_response("Fish type not found", status_code=404)

    data = request.form.to_dict()
    image_file = request.files.get('image')
    upload_folder = current_app.config['UPLOAD_FOLDER']

    return FishTypeService.update(fish_type, data, image_file=image_file, upload_folder=upload_folder, performed_by=get_performed_by())

@bp.route('/<int:type_id>', methods=['DELETE'])
def delete_fish_type(type_id):
    return FishTypeService.delete(type_id, performed_by=get_performed_by())


# @bp.route('', methods=['POST'])
# def create_fish_type():
#     # Get form data
#     data = request.form
    
#     # Validate using model method
#     validation_errors = FishType.validate_fields(data)
#     if validation_errors:
#         return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)
    
#     # Handle image upload
#     image_url = None
#     if 'image' in request.files:
#         file = request.files['image']
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             # Add timestamp to filename to avoid duplicates
#             filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
#             file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
#             file.save(file_path)
#             image_url = f"/uploads/fish_images/{filename}"
    
#     is_active = data.get('isActive', 'true').lower() == 'true'
    
#     size = None
#     if 'size' in data and data.get('size'):
#         from app.models.fish_type import FishSize
#         try:
#             size = FishSize(data.get('size'))
#         except ValueError:
#             # If invalid size, validation should have caught it
#             pass

#     # Create new fish type
#     new_fish_type = FishType(
#         type_code=FishType.generate_type_code(),
#         common_name=data.get('commonName'),
#         scientific_name=data.get('scientificName'),
#         size=size,
#         image_url=image_url,
#         is_active=is_active,
#         created_at=datetime.utcnow()
#     )
    
#     db.session.add(new_fish_type)
#     db.session.commit()
    
#     return api_response("Fish type created successfully", data=new_fish_type.to_dict(), status_code=201)


# @bp.route('<int:type_id>', methods=['PUT'])
# def update_fish_type(type_id):
#     fish_type = FishType.query.get(type_id)
#     data = request.form
    
#     print("Received data:", data)

#     # Validate only updatable fields
#     validation_errors = FishType.validate_fields(data, for_update=True)
#     if validation_errors:
#         return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)
        
#     # Handle image upload
#     if 'image' in request.files:
#         file = request.files['image']
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             # Add timestamp to filename to avoid duplicates
#             filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
#             file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
#             file.save(file_path)
#             fish_type.image_url = f"/uploads/fish_images/{filename}"

#     is_active = data.get('isActive', str(fish_type.is_active)).lower() == 'true'  # Default to current value if not provided

#     # Handle size if provided
#     if 'size' in data:
#         from app.models.fish_type import FishSize
#         if data.get('size'):
#             try:
#                 fish_type.size = FishSize(data.get('size'))
#             except ValueError:
#                 # If invalid size, validation should have caught it
#                 pass
#         else:
#             fish_type.size = None

#     # Update fields if provided
#     # if 'typeCode' in data:
#     #     fish_type.type_code = data.get('typeCode').upper()
#     if 'commonName' in data:
#         fish_type.common_name = data.get('commonName')
#     if 'scientificName' in data:
#         fish_type.scientific_name = data.get('scientificName')

#     # Update the is_active field
#     fish_type.is_active = is_active

#     fish_type.updated_at = datetime.utcnow()
#     db.session.commit()
    
#     return api_response("Fish type updated successfully", data=fish_type.to_dict())
