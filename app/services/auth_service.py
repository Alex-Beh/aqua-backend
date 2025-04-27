from app.services.user_service import get_user_by_username
from app.utils.password_utils import hash_password, verify_password

def authenticate_user(username, password):
    user = get_user_by_username(username)
    if not user:
        return None, "Invalid credentials"

    if not verify_password(user.password_hash, password):
        return None, "Invalid credentials"

    if not user.is_active:
        return None, "Account is inactive or resigned"

    return user, None
