from flask import Blueprint, request, jsonify
from app.models import Company, Site
from app import db
from datetime import datetime
from app.services.site_service import SiteService
from app.utils import api_response, validate_json, paginate_response
from flask_login import current_user, login_required
from app.decorators.roles import admin_required

bp = Blueprint('site', __name__, url_prefix='/api/sites')

# # Apply login_required globally for all routes in this blueprint
# @bp.before_request
# @login_required
# def before_request():
#     pass

# Get a paginated list of sites (optionally filtered by company_id)
@bp.route('/paging', methods=['GET'])
def get_sites_paged():
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 10, type=int)
    company_id = request.args.get('companyId', type=int)
    sort_field = request.args.get('sortField', 'site_name')
    sort_order = request.args.get('sortOrder', 'asc')

    paginated_data = SiteService.get_sites_paged(page, size, sort_field, sort_order, company_id)

    return api_response(
        "Sites retrieved successfully",
        data=paginated_data
    )

# Get all sites (optionally filtered by company_id)
@bp.route('/', methods=['GET'])
def get_all_sites():
    company_id = request.args.get('companyId', type=int)
    sites = SiteService.get_all_sites(company_id)
    return api_response("Sites retrieved successfully", data=sites)

# Get a single site
@bp.route('/<int:site_id>', methods=['GET'])
def get_site(site_id):
    site = SiteService.get_site(site_id)
    if not site:
        return api_response("Site not found", status_code=404)
    return api_response("Site retrieved successfully", data=site)

# Create a new site
@bp.route('', methods=['POST'])
# @admin_required
def create_site():
    data = request.get_json()
    return SiteService.create_site(data, user_id=current_user.id)

# Update a site
@bp.route('/<int:site_id>', methods=['PUT'])
# @admin_required
def update_site(site_id):
    data = request.get_json()
    return SiteService.update_site(site_id, data, user_id=current_user.id)

# Soft delete a site
@bp.route('/<int:site_id>', methods=['DELETE'])
# @admin_required
def delete_site(site_id):
    return SiteService.delete_site(site_id, user_id=current_user.id)
