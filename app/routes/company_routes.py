from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from app.decorators.roles import admin_required
from app.models import Company, Site
from app import db
from datetime import datetime
from app.services.company_service import CompanyService
from app.utils import api_response, validate_json, paginate_response

bp = Blueprint('company', __name__, url_prefix='/api/companies')

# Apply login_required globally for all routes in this blueprint
@bp.before_request
@login_required
def before_request():
    pass

# API Routes - Company
@bp.route('paging', methods=['GET'])
def get_companies_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    sort_field = request.args.get('sortField', 'company_name')  # Default sorting by company_name
    sort_order = request.args.get('sortOrder', 'asc')  # Default ascending order

    # Call service layer for paginated data
    paginated_data = CompanyService.get_companies_paged(page, size, sort_field, sort_order)

    return api_response(
        "Companies retrieved successfully",
        data=paginated_data
    )

# Get all companies
@bp.route('', methods=['GET'])
def get_all_companies():
    # Call service layer to get all companies
    companies = CompanyService.get_all_companies()
    return api_response("Companies retrieved successfully", data=companies)

# Get a paginated list of sites for a company
@bp.route('<int:company_id>/sites/paging', methods=['GET'])
def get_sites_paged(company_id):
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    sort_field = request.args.get('sortField', 'site_name')  # Assuming 'site_name' is the field you want to sort by
    sort_order = request.args.get('sortOrder', 'asc')  # Default to 'asc'

    # Call service layer to get paginated sites for a company
    paginated_data = CompanyService.get_sites_paged(company_id, page, size, sort_field, sort_order)

    return api_response(
        "Sites retrieved successfully",
        data=paginated_data
    )

# Get all sites for a company
@bp.route('<int:company_id>/sites', methods=['GET'])
def get_all_sites(company_id):
    # Call service layer to get all sites for a company
    sites = CompanyService.get_all_sites(company_id)
    return api_response("Sites retrieved successfully", data=sites)

# Get a single company
@bp.route('<int:company_id>', methods=['GET'])
@admin_required
def get_company(company_id):
    # Call service layer to get a company
    company = CompanyService.get_company(company_id)
    if not company:
        return api_response("Company not found", status_code=404)
    return api_response("Company retrieved successfully", data=company)

# Create a company
@bp.route('', methods=['POST'])
@admin_required
def create_company():
    data = request.get_json()
    return CompanyService.create_company(data, current_user.id)

# Update a company
@bp.route('<int:company_id>', methods=['PUT'])
@admin_required
def update_company(company_id):
    data = request.get_json()
    return CompanyService.update_company(company_id, data, current_user.id)

# Delete a company (soft delete)
@bp.route('<int:company_id>', methods=['DELETE'])
@admin_required
def delete_company(company_id):
    return CompanyService.delete_company(company_id, current_user.id)