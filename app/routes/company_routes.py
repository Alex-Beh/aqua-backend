from flask import Blueprint, request, jsonify
from app.models import Company, Site
from app import db
from datetime import datetime
from app.utils import api_response, validate_json, paginate_response

bp = Blueprint('company', __name__, url_prefix='/api/companies')

# API Routes - Company

@bp.route('paging', methods=['GET'])
def get_companies_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    sort_field = request.args.get('sortField', 'company_name')  # Default sorting by company_name
    sort_order = request.args.get('sortOrder', 'asc')  # Default ascending order

    query = Company.query.filter(Company.deleted_at.is_(None))
    paginated_data = paginate_response(query, page, size, Company, sort_field, sort_order)

    return api_response(
        "Companies retrieved successfully",
        data=paginated_data
    )

# Get all companies
@bp.route('', methods=['GET'])
def get_all_companies():
    items = Company.query.filter(Company.deleted_at.is_(None)).all()
    return api_response("Companies retrieved successfully", data=[c.to_dict() for c in items])

# Get a paginated list of sites for a company
@bp.route('<int:company_id>/sites/paging', methods=['GET'])
def get_sites_paged(company_id):
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    sort_field = request.args.get('sortField', 'site_name')  # Assuming 'site_name' is the field you want to sort by
    sort_order = request.args.get('sortOrder', 'asc')  # Default to 'asc'

    # Construct the query
    query = Site.query.filter(Site.company_id == company_id, Site.deleted_at.is_(None))

    # Use the paginate_response function to handle pagination and sorting
    paginated_data = paginate_response(query, page, size, Site, sort_field, sort_order)

    return api_response(
        "Sites retrieved successfully",
        data=paginated_data
    )

# Get a single company
@bp.route('<int:company_id>', methods=['GET'])
def get_company(company_id):
    company = Company.query.get(company_id)
    if not company or company.deleted_at:
        return api_response("Company not found", status_code=404)
    return api_response("Company retrieved successfully", data=company.to_dict())

# Create a company
@bp.route('', methods=['POST'])
def create_company():
    data = request.get_json()

    validation_errors = Company.validate_fields(data)
    if validation_errors:
        return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)
    
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
    return api_response("Company created successfully", data=new_company.to_dict(), status_code=201)

# Update a company
@bp.route('<int:company_id>', methods=['PUT'])
def update_company(company_id):
    company = Company.query.get(company_id)
    if not company or company.deleted_at:
        return api_response("Company not found", status_code=404)
    
    data = request.get_json()

    validation_errors = Company.validate_fields(data, for_update=True)
    if validation_errors:
        return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)

    company.company_name = data.get('companyName', company.company_name)
    company.hotline = data.get('hotline', company.hotline)
    company.email = data.get('email', company.email)
    company.address = data.get('address', company.address)
    company.updated_at = datetime.utcnow()
    db.session.commit()
    return api_response("Company updated successfully", data=company.to_dict())

# Delete a company (soft delete)
@bp.route('<int:company_id>', methods=['DELETE'])
def delete_company(company_id):
    company = Company.query.get(company_id)
    if not company or company.deleted_at:
        return api_response("Company not found", status_code=404)
    
    if not company.can_be_deleted():
        return api_response("Cannot delete: Company still has active sites.", status_code=400)
    
    company.soft_delete()
    db.session.commit()
    
    return api_response("Company deleted successfully")

# Get all sites for a company
@bp.route('<int:company_id>/sites', methods=['GET'])
def get_all_sites(company_id):
    sites = Site.query.filter(Site.company_id == company_id, Site.deleted_at.is_(None)).all()
    return api_response("Sites retrieved successfully", data=[s.to_dict() for s in sites])