from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost:5432/aquastock'
app.config['UPLOAD_FOLDER'] = 'uploads/fish_images'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload size
db = SQLAlchemy(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Fish Type model
class FishType(db.Model):
    __tablename__ = 'fish_types'
    
    type_id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.String(20), unique=True, nullable=False)
    common_name = db.Column(db.String(100), nullable=False)
    scientific_name = db.Column(db.String(100))
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'typeId': self.type_id,
            'typeCode': self.type_code,
            'commonName': self.common_name,
            'scientificName': self.scientific_name,
            'imageUrl': self.image_url,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'isActive': self.is_active
        }

# Helper function for file upload
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# API Routes
@app.route('/api/fish-types', methods=['GET'])
def get_fish_types():
    fish_types = FishType.query.filter_by(is_active=True).all()
    return jsonify([fish_type.to_dict() for fish_type in fish_types])

@app.route('/api/fish-types/<int:type_id>', methods=['GET'])
def get_fish_type(type_id):
    fish_type = FishType.query.get_or_404(type_id)
    if not fish_type.is_active:
        return jsonify({'error': 'Fish type not found'}), 404
    return jsonify(fish_type.to_dict())

@app.route('/api/fish-types', methods=['POST'])
def create_fish_type():
    # Get form data
    data = request.form
    
    # Check if type_code exists
    if FishType.query.filter_by(type_code=data.get('typeCode')).first():
        return jsonify({'error': 'Type code already exists'}), 400
    
    # Handle image upload
    image_url = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to avoid duplicates
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
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

@app.route('/api/fish-types/<int:type_id>', methods=['PUT'])
def update_fish_type(type_id):
    fish_type = FishType.query.get_or_404(type_id)
    data = request.form
    
    # Handle image upload
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to avoid duplicates
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            fish_type.image_url = f"/uploads/fish_images/{filename}"
    
    # Update fields if provided
    if 'typeCode' in data:
        fish_type.type_code = data.get('typeCode').upper()
    if 'commonName' in data:
        fish_type.common_name = data.get('commonName')
    if 'scientificName' in data:
        fish_type.scientific_name = data.get('scientificName')
    
    fish_type.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(fish_type.to_dict())

@app.route('/api/fish-types/<int:type_id>', methods=['DELETE'])
def delete_fish_type(type_id):
    fish_type = FishType.query.get_or_404(type_id)
    
    # Soft delete - just mark as inactive
    fish_type.is_active = False
    fish_type.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Fish type deleted successfully'}), 200

# Run the server
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True)
