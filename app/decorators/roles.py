from functools import wraps
from flask import abort
from flask_login import current_user
from app.utils import api_response

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            # Return a custom response with api_response
            return api_response(
                "You do not have permission to access this resource", 
                status_code=403
            )
        return f(*args, **kwargs)
    return decorated_function