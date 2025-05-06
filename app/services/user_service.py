from app.models.app_user import AppUser
from app import db
from app.utils.password_utils import hash_password, verify_password
from flask_login import current_user

def create_user(username, password, roleId, staffId=None, name=None, emailId=None, phoneNumber=None):
    # Hash the password before storing
    hashed_password = hash_password(password)
    
    new_user = AppUser(
        username=username,
        name=name,
        emailid=emailId if emailId else None,  # Optional field
        staff_id=staffId if staffId else None,  # Optional field
        phone_number=phoneNumber if phoneNumber else None,  # Optional field
        password_hash=hashed_password,
        status='Active',  # Default status
        role_id=roleId,
        created_by=current_user.id if current_user.is_authenticated else None
    )
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return new_user
    except Exception as e:
        raise Exception(f"Error creating user: {str(e)}")
    
def validate_and_create_user(data, performed_by=None):
    validation_errors = validate_user_data(data)
    if validation_errors:
        return None, validation_errors

    ## TODO(06 May): We gave the user different signup code for different roleId, for staffId, we can assign the same value from username
    # Validate the signup code
    expected_signup_code = "ABC123"
    if data.get("signupCode") != expected_signup_code:
        return None, ["Invalid signup code"]

    try:
        new_user = create_user(
            username=data['username'],
            password=data['password'],
            roleId=data['roleId'],
            staffId=data.get('staffId'),
            name=data.get('name'),
            emailId=data.get('emailId'),
            phoneNumber=data.get('phoneNumber'),
            created_by=performed_by,
            created_at=db.func.current_timestamp()
        )
        return new_user, None
    except Exception as e:
        return None, [str(e)]

def get_user_by_username(username):
    return AppUser.query.filter_by(username=username).first()

def check_user_password(user, password):
    return verify_password(user.password_hash, password)

def validate_user_data(data, for_update=False):
    errors = {}

    # Validate username
    if not data.get('username'):
        errors['username'] = "Username is required"
    else:
        existing_user = AppUser.query.filter_by(username=data['username']).first()
        if existing_user and not for_update:
            errors['username'] = "Username already taken"

    # Validate name
    name = data.get('name')
    if name and len(name) > 100:
        errors['name'] = "Name cannot be more than 100 characters"

    # Validate password
    password = data.get('password')
    if not password:
        errors['password'] = "Password is required"
    # elif len(password) < 8:
    #     errors['password'] = "Password must be at least 8 characters long"
    # elif not any(char.isdigit() for char in password):
    #     errors['password'] = "Password must contain at least one number"
    # elif not any(char.isalpha() for char in password):
    #     errors['password'] = "Password must contain at least one letter"

    # Validate role_id
    # role_id = data.get('roleId')
    # if role_id is None or role_id <= 0:
    #     errors['roleId'] = "Role is required"
    # else:
    #     from app.models.role import Role  # lazy import to avoid circular import
    #     role = Role.query.filter_by(role_id=role_id).first()
    #     if not role:
    #         errors['roleId'] = "Invalid Role provided"

    # Optionally validate emailid format if provided
    emailid = data.get('emailid')
    if emailid and '@' not in emailid:
        errors['emailid'] = "Invalid email format"

    return errors if errors else None
