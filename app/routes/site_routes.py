from flask import Blueprint, request, jsonify
from app.models import Company, Site
from app import db
from datetime import datetime
from app.utils import api_response, validate_json, paginate_response

bp = Blueprint('site', __name__, url_prefix='/api/sites')

# Get a paginated list of sites (optionally filtered by company_id)
@bp.route('paging', methods=['GET'])
def get_sites_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    company_id = request.args.get('companyId', type=int)  # Optional filter by companyId
    sort_field = request.args.get('sortField', 'site_name')  # Default sorting by site_name
    sort_order = request.args.get('sortOrder', 'asc')  # Default to ascending order

    # Construct the query
    query = Site.query.filter(Site.deleted_at.is_(None))

    if company_id:
        query = query.filter_by(company_id=company_id)

    # Use the paginate_response function to handle pagination and sorting
    paginated_data = paginate_response(query, page, size, Site, sort_field, sort_order)

    return api_response("Sites retrieved successfully", data=paginated_data)

# Get all sites (optionally filtered by company_id)
@bp.route('', methods=['GET'])
def get_all_sites():
    company_id = request.args.get('companyId', type=int)

    query = Site.query.filter(Site.deleted_at.is_(None))

    if company_id:
        query = query.filter_by(company_id=company_id)

    sites = query.order_by(Site.site_name.asc()).all()
    return api_response("Sites retrieved successfully", data=[site.to_dict() for site in sites])

# Get a single site
@bp.route('<int:site_id>', methods=['GET'])
def get_site(site_id):
    site = Site.query.get(site_id)
    # Check if the site exists and isn't marked as deleted
    if not site or site.deleted_at:
        return api_response("Site not found", status_code=404)
    
    return api_response("Site retrieved successfully", data=site.to_dict())

# Create a new site
@bp.route('', methods=['POST'])
def create_site():
    data = request.get_json()

    # Validate using model method
    validation_errors  = Site.validate_fields(data)
    if validation_errors :
        return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)

    new_site = Site(
        company_id=data.get('companyId'),
        site_name=data.get('siteName'),
        site_code=data.get('siteCode').upper(),
        location=data.get('location'),
        hotline=data.get('hotline'),
        site_manager_id=data.get('siteManagerId'),
        site_contact_id=data.get('siteContactId'),
        # created_by=data.get('createdBy'),
        created_at=datetime.utcnow()
    )

    db.session.add(new_site)
    db.session.commit()
    return api_response("Site created successfully", data=new_site.to_dict(), status_code=201)

# Update a site
@bp.route('<int:site_id>', methods=['PUT'])
def update_site(site_id):
    site = Site.query.get(site_id)
    if not site or site.deleted_at:
        return api_response("Site not found", status_code=404)
        
    data = request.get_json()

    # Perform validation (for update case)
    validation_errors = Site.validate_fields(data, for_update=True)
    if validation_errors:
        return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)

    site.site_name = data.get('siteName', site.site_name)
    site.location = data.get('location', site.location)
    site.hotline = data.get('hotline', site.hotline)
    site.site_manager_id = data.get('siteManagerId', site.site_manager_id)
    site.site_contact_id = data.get('siteContactId', site.site_contact_id)
    site.updated_at = datetime.utcnow()

    db.session.commit()
    return api_response("Site updated successfully", data=site.to_dict())

# Soft delete a site
@bp.route('<int:site_id>', methods=['DELETE'])
def delete_site(site_id):
    site = Site.query.get(site_id)
    if not site or site.deleted_at:
        return api_response("Site not found", status_code=404)
    
    site.soft_delete()
    db.session.commit()
    return api_response("Site deleted successfully")

