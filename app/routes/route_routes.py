from flask import Blueprint
from app.models import Role
from app.utils import api_response
from flask_login import login_required

role_bp = Blueprint('role', __name__, url_prefix='/api/roles')

# # Apply login_required globally for all role routes
# @role_bp.before_request
# @login_required
# def before_request():
#     pass

@role_bp.route('', methods=['GET'])
def get_all_roles():
    roles = Role.query.all()
    role_list = [role.to_dict() for role in roles]
    return api_response("Roles retrieved successfully", data=role_list)