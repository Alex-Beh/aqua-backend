from flask import Blueprint, request, jsonify
from app.models import Company, Site
from app import db
from datetime import datetime

bp = Blueprint('company', __name__, url_prefix='/api/companies')

# API Routes - Company
# Get all companies
@bp.route('', methods=['GET'])
def get_all_companies():
    items = Company.query.filter(Company.deleted_at.is_(None)).all()
    return jsonify([c.to_dict() for c in items])

@bp.route('paging', methods=['GET'])
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
@bp.route('<int:company_id>', methods=['GET'])
def get_company(company_id):
    company = Company.query.get_or_404(company_id)
    if company.deleted_at:
        return jsonify({'error': 'Company not found'}), 404
    return jsonify(company.to_dict())

# Create a company
@bp.route('', methods=['POST'])
def create_company():
    data = request.get_json()

    errors = Company.validate_fields(data)
    if errors:
        return jsonify({'errors': errors}), 400
    
    new_company = Company(
        company_name=data.get('companyName'),
        company_code=data.get('companyCode').upper(),
        hotline=data.get('hotline'),
        email=data.get('email'),
        address=data.get('address'),
        created_at=datetime.utcnow()
    )
    db.session.add(new_company)
    db.session.commit()
    return jsonify(new_company.to_dict()), 201

# Update a company
@bp.route('<int:company_id>', methods=['PUT'])
def update_company(company_id):
    company = Company.query.get_or_404(company_id)
    data = request.get_json()

    errors = Company.validate_fields(data, for_update=True)
    if errors:
        return jsonify({'errors': errors}), 400

    company.company_name = data.get('companyName', company.company_name)
    company.hotline = data.get('hotline', company.hotline)
    company.email = data.get('email', company.email)
    company.address = data.get('address', company.address)
    company.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(company.to_dict())

# Delete a company (soft delete)
@bp.route('<int:company_id>', methods=['DELETE'])
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)

    company.soft_delete()
    db.session.commit()
    
    return jsonify({'message': 'Company deleted successfully'}), 200

# Get all sites for a company
@bp.route('<int:company_id>/sites', methods=['GET'])
def get_all_sites(company_id):
    sites = Site.query.filter(Site.company_id == company_id, Site.deleted_at.is_(None)).all()
    return jsonify([s.to_dict() for s in sites])

# Get a paginated list of sites for a company
@bp.route('<int:company_id>/sites/paging', methods=['GET'])
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