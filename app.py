from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
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
migrate = Migrate(app, db)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Company model
class Company(db.Model):
    __tablename__ = 'company'

    company_id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    company_code = db.Column(db.String(50), unique=True, nullable=False)
    hotline = db.Column(db.String(50))
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime)
    deleted_by = db.Column(db.Integer)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'companyId': self.company_id,
            'companyName': self.company_name,
            'companyCode': self.company_code,
            'hotline': self.hotline,
            'email': self.email,
            'address': self.address,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedBy': self.updated_by,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'deletedBy': self.deleted_by,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None,
        }

# Site model
class Site(db.Model):
    __tablename__ = 'site'

    site_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.company_id'))
    site_name = db.Column(db.String(100), nullable=False)
    site_code = db.Column(db.String(50), unique=True, nullable=False)
    location = db.Column(db.String(200))
    hotline = db.Column(db.String(50))
    site_manager_id = db.Column(db.Integer)
    site_contact_id = db.Column(db.Integer)
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime)
    deleted_by = db.Column(db.Integer)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'siteId': self.site_id,
            'companyId': self.company_id,
            'siteName': self.site_name,
            'siteCode': self.site_code,
            'location': self.location,
            'hotline': self.hotline,
            'siteManagerId': self.site_manager_id,
            'siteContactId': self.site_contact_id,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedBy': self.updated_by,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'deletedBy': self.deleted_by,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None,
        }
    
# Fish Type 
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

# API Routes - Company
# Get all companies
@app.route('/api/companies', methods=['GET'])
def get_all_companies():
    items = Company.query.filter(Company.deleted_at.is_(None)).all()
    return jsonify([c.to_dict() for c in items])

@app.route('/api/companies/paging', methods=['GET'])
def get_companies_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)

    query = Company.query.filter(Company.deleted_at.is_(None))
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()

    return jsonify({
        'total': total,
        'page': page,
        'size': size,
        'data': [c.to_dict() for c in items]
    })

# Get a single company
@app.route('/api/companies/<int:company_id>', methods=['GET'])
def get_company(company_id):
    company = Company.query.get_or_404(company_id)
    if company.deleted_at:
        return jsonify({'error': 'Company not found'}), 404
    return jsonify(company.to_dict())

# Create a company
@app.route('/api/companies', methods=['POST'])
def create_company():
    data = request.get_json()

    if not data.get('companyName') or not data.get('companyCode') or not data.get('createdBy'):
        return jsonify({'error': 'Missing required fields'}), 400

    if Company.query.filter_by(company_code=data.get('companyCode').upper()).first():
        return jsonify({'error': 'Company code already exists'}), 400

    new_company = Company(
        company_name=data.get('companyName'),
        company_code=data.get('companyCode').upper(),
        hotline=data.get('hotline'),
        email=data.get('email'),
        address=data.get('address'),
        created_by=data.get('createdBy'),
        created_at=datetime.utcnow()
    )
    db.session.add(new_company)
    db.session.commit()
    return jsonify(new_company.to_dict()), 201

# Update a company
@app.route('/api/companies/<int:company_id>', methods=['PUT'])
def update_company(company_id):
    company = Company.query.get_or_404(company_id)
    data = request.get_json()

    if not data.get('companyName') or not data.get('createdBy'):
        return jsonify({'error': 'Missing required fields'}), 400

    company.company_name = data.get('companyName', company.company_name)
    company.hotline = data.get('hotline', company.hotline)
    company.email = data.get('email', company.email)
    company.address = data.get('address', company.address)
    company.updated_by = data.get('updatedBy')
    company.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(company.to_dict())

# Delete a company (soft delete)
@app.route('/api/companies/<int:company_id>', methods=['DELETE'])
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)
    company.deleted_by = request.args.get('deletedBy', type=int)
    company.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Company deleted successfully'}), 200

# Get all sites for a company
@app.route('/api/companies/<int:company_id>/sites', methods=['GET'])
def get_all_sites(company_id):
    sites = Site.query.filter(Site.company_id == company_id, Site.deleted_at.is_(None)).all()
    return jsonify([s.to_dict() for s in sites])

# Get a paginated list of sites for a company
@app.route('/api/companies/<int:company_id>/sites/paging', methods=['GET'])
def get_sites_paged(company_id):
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)

    query = Site.query.filter(Site.company_id == company_id, Site.deleted_at.is_(None))
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()

    return jsonify({
        'total': total,
        'page': page,
        'size': size,
        'data': [s.to_dict() for s in items]
    })

# Get a single site
@app.route('/api/sites/<int:site_id>', methods=['GET'])
def get_site(site_id):
    site = Site.query.get_or_404(site_id)
    if site.deleted_at:
        return jsonify({'error': 'Site not found'}), 404
    return jsonify(site.to_dict())

# Create a new site
@app.route('/api/sites', methods=['POST'])
def create_site():
    data = request.get_json()

    if not data.get('companyId') or not data.get('siteName') or not data.get('siteCode') or not data.get('createdBy'):
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate company existence
    company = Company.query.filter_by(company_id=data.get('companyId'), deleted_at=None).first()
    if not company:
        return jsonify({'error': 'Invalid or deleted company ID'}), 400

    if Site.query.filter_by(site_code=data.get('siteCode').upper()).first():
        return jsonify({'error': 'Site code already exists'}), 400

    new_site = Site(
        company_id=data.get('companyId'),
        site_name=data.get('siteName'),
        site_code=data.get('siteCode').upper(),
        location=data.get('location'),
        hotline=data.get('hotline'),
        site_manager_id=data.get('siteManagerId'),
        site_contact_id=data.get('siteContactId'),
        created_by=data.get('createdBy'),
        created_at=datetime.utcnow()
    )

    db.session.add(new_site)
    db.session.commit()
    return jsonify(new_site.to_dict()), 201


# Update a site
@app.route('/api/sites/<int:site_id>', methods=['PUT'])
def update_site(site_id):
    site = Site.query.get_or_404(site_id)
    data = request.get_json()

    # If company_id is provided, validate it first
    new_company_id = data.get('companyId')
    if new_company_id and new_company_id != site.company_id:
        company = Company.query.filter_by(company_id=new_company_id, deleted_at=None).first()
        if not company:
            return jsonify({'error': 'Invalid or deleted company ID'}), 400
        site.company_id = new_company_id

    site.site_name = data.get('siteName', site.site_name)
    site.location = data.get('location', site.location)
    site.hotline = data.get('hotline', site.hotline)
    site.site_manager_id = data.get('siteManagerId', site.site_manager_id)
    site.site_contact_id = data.get('siteContactId', site.site_contact_id)
    site.updated_by = data.get('updatedBy')
    site.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify(site.to_dict())

# Soft delete a site
@app.route('/api/sites/<int:site_id>', methods=['DELETE'])
def delete_site(site_id):
    site = Site.query.get_or_404(site_id)
    site.deleted_by = request.args.get('deletedBy', type=int)
    site.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Site deleted successfully'}), 200

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
