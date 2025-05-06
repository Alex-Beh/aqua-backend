from flask import Blueprint, request, jsonify
from app.models.app_user import AppUser
from app import db
from flask_login import login_user, logout_user, login_required, current_user
from app.models.role import Role
from app.services.auth_service import authenticate_user
from app.services.user_service import validate_and_create_user
from app.utils import api_response

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def get_performed_by():
    return current_user.name if current_user.is_authenticated else "Anonymous"

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json

    user, error = authenticate_user(data['username'], data['password'])

    if error:
        return api_response(error, status_code=401) 

    login_user(user)
    
    ## TODO: need to convert the role_id and represent it as a string, then return it
    return api_response(
        "Logged in successfully", data={"role": user.staff_id}, status_code=200)

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return api_response("Logged out successfully", status_code=200)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    new_user, validation_errors = validate_and_create_user(data, performed_by=get_performed_by())

    if validation_errors:
        return api_response("One or more validation errors occurred", errors=validation_errors, status_code=400)

    return api_response("User created successfully", data=new_user.to_dict(), status_code=201)
