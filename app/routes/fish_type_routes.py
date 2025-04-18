from flask import Blueprint, request, jsonify, send_from_directory, current_app
from app.models import FishType
from app import db
from datetime import datetime
from werkzeug.utils import secure_filename
import os

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
@bp.route('', methods=['GET'])
def get_fish_types():
    fish_types = FishType.query.filter(FishType.deleted_at.is_(None)).all()
    return jsonify([fish_type.to_dict() for fish_type in fish_types])

@bp.route('<int:type_id>', methods=['GET'])
def get_fish_type(type_id):
    fish_type = FishType.query.get_or_404(type_id)
    if fish_type.deleted_at:
        return jsonify({'error': 'Fish type not found'}), 404
    return jsonify(fish_type.to_dict())

@bp.route('', methods=['POST'])
def create_fish_type():
    # Get form data
    data = request.form
    
    # Validate using model method
    errors = FishType.validate_fields(data)
    if errors:
        return jsonify({'errors': errors}), 400
    
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
    
    # Create new fish type
    new_fish_type = FishType(
        type_code=data.get('typeCode').upper(),
        common_name=data.get('commonName'),
        scientific_name=data.get('scientificName'),
        image_url=image_url
    )
    
    db.session.add(new_fish_type)
    db.session.commit()
    
    return jsonify(new_fish_type.to_dict()), 201

@bp.route('<int:type_id>', methods=['PUT'])
def update_fish_type(type_id):
    fish_type = FishType.query.get_or_404(type_id)
    data = request.form
    
    # Validate only updatable fields
    errors = FishType.validate_fields(data, for_update=True)
    if errors:
        return jsonify({'errors': errors}), 400
        
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
    
    # Update fields if provided
    # if 'typeCode' in data:
    #     fish_type.type_code = data.get('typeCode').upper()
    if 'commonName' in data:
        fish_type.common_name = data.get('commonName')
    if 'scientificName' in data:
        fish_type.scientific_name = data.get('scientificName')
    
    fish_type.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(fish_type.to_dict())

@bp.route('<int:type_id>', methods=['DELETE'])
def delete_fish_type(type_id):
    # if not current_user.is_admin:  # Add your auth check
    #     return jsonify({'error': 'Unauthorized'}), 403
    
    fish_type = FishType.query.get_or_404(type_id)
    
    fish_type.soft_delete()
    db.session.commit()
    
    return jsonify({'message': 'Fish type deleted successfully'}), 200
