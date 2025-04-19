from flask import Blueprint, request, jsonify, send_from_directory, current_app
from app.models import FishType
from app import db
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from app.utils import api_response, validate_json, paginate_response

# Helper function for file upload
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

static_bs = Blueprint('static_files', __name__)
@static_bs.route('/uploads/fish_images/<filename>')
def serve_fish_image(filename):
    

    print(f"Serving file: {filename}")
    if os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], filename)):
        print("File exists")
    else: 
        print("File does not exist")

    upload_folder = os.path.abspath(current_app.config['UPLOAD_FOLDER'])  # Absolute path

    return send_from_directory(upload_folder, filename)

bp = Blueprint('fish_types', __name__, url_prefix='/api/fish-types')

# API Routes
# Get a paginated list of fish types (optionally filtered by status)
@bp.route('/paging', methods=['GET'])
def get_fish_types_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    status = request.args.get('status')  # active or inactive
    sort_field = request.args.get('sortField', 'type_code')  # Default sorting by type_code
    sort_order = request.args.get('sortOrder', 'asc')  # Default ascending order

    query = FishType.query.filter(FishType.deleted_at.is_(None))

    # Apply status filter if present
    if status == 'active':
        query = query.filter(FishType.is_active.is_(True))
    elif status == 'inactive':
        query = query.filter(FishType.is_active.is_(False))

    # Use paginate_response function to handle pagination
    paginated_data = paginate_response(query, page, size, FishType, sort_field, sort_order)

    return api_response("Fish types retrieved successfully", data=paginated_data)

# Get all fish types
@bp.route('', methods=['GET'])
def get_fish_types():
    status = request.args.get('status')  # active or inactive

    query = FishType.query.filter(FishType.deleted_at.is_(None))
    if status == 'active':
        query = query.filter(FishType.is_active.is_(True))
    elif status == 'inactive':
        query = query.filter(FishType.is_active.is_(False))

    items = query.all()
    return api_response("Fish types retrieved successfully", data=[f.to_dict() for f in items])

@bp.route('<int:type_id>', methods=['GET'])
def get_fish_type(type_id):
    fish_type = FishType.query.get(type_id)
    if not fish_type or fish_type.deleted_at:
        return api_response("Fish type not found", status_code=404)
    return api_response("Fish type retrieved successfully", data=fish_type.to_dict())

@bp.route('', methods=['POST'])
def create_fish_type():
    # Get form data
    data = request.form
    
    # Validate using model method
    validation_errors = FishType.validate_fields(data)
    if validation_errors:
        return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)
    
    # Handle image upload
    image_url = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to avoid duplicates
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_url = f"/uploads/fish_images/{filename}"
    
    is_active = data.get('isActive', 'true').lower() == 'true'

    # Create new fish type
    new_fish_type = FishType(
        type_code=FishType.generate_type_code(),
        common_name=data.get('commonName'),
        scientific_name=data.get('scientificName'),
        image_url=image_url,
        is_active=is_active,
        created_at=datetime.utcnow()
    )
    
    db.session.add(new_fish_type)
    db.session.commit()
    
    return api_response("Fish type created successfully", data=new_fish_type.to_dict(), status_code=201)

@bp.route('<int:type_id>', methods=['PUT'])
def update_fish_type(type_id):
    fish_type = FishType.query.get(type_id)
    data = request.form
    
    # Validate only updatable fields
    validation_errors = FishType.validate_fields(data, for_update=True)
    if validation_errors:
        return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)
        
    # Handle image upload
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to avoid duplicates
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            fish_type.image_url = f"/uploads/fish_images/{filename}"

    is_active = data.get('isActive', str(fish_type.is_active)).lower() == 'true'  # Default to current value if not provided

    # Update fields if provided
    # if 'typeCode' in data:
    #     fish_type.type_code = data.get('typeCode').upper()
    if 'commonName' in data:
        fish_type.common_name = data.get('commonName')
    if 'scientificName' in data:
        fish_type.scientific_name = data.get('scientificName')

    # Update the is_active field
    fish_type.is_active = is_active

    fish_type.updated_at = datetime.utcnow()
    db.session.commit()
    
    return api_response("Fish type updated successfully", data=fish_type.to_dict())

@bp.route('<int:type_id>', methods=['DELETE'])
def delete_fish_type(type_id):
    # if not current_user.is_admin:  # Add your auth check
    #     return jsonify({'error': 'Unauthorized'}), 403
    
    fish_type = FishType.query.get(type_id)
    if not fish_type or fish_type.deleted_at:
        return api_response("Fish type not found", status_code=404)
    
    fish_type.soft_delete()
    db.session.commit()
    
    return api_response("Fish type deleted successfully")