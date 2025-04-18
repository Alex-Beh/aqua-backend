from flask import Blueprint, request, jsonify
from app.models import Company, Site
from app import db
from datetime import datetime

bp = Blueprint('site', __name__, url_prefix='/api/sites')

# Get a single site
@bp.route('<int:site_id>', methods=['GET'])
def get_site(site_id):
    site = Site.query.get_or_404(site_id)
    if site.deleted_at:
        return jsonify({'error': 'Site not found'}), 404
    return jsonify(site.to_dict())

# Create a new site
@bp.route('/api/sites', methods=['POST'])
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
@bp.route('<int:site_id>', methods=['PUT'])
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
@bp.route('<int:site_id>', methods=['DELETE'])
def delete_site(site_id):
    site = Site.query.get_or_404(site_id)
    site.deleted_by = request.args.get('deletedBy', type=int)
    site.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Site deleted successfully'}), 200
