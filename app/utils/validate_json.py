from flask import request

def validate_json(required_fields=None):
    """
    Validates if the incoming request has valid JSON and checks for required fields.
    :param required_fields: List of required fields to validate
    :return: List of error messages if validation fails
    """
    errors = []
    
    # Check if request contains valid JSON
    if not request.is_json:
        errors.append("Request must be in JSON format")
    
    # Check if the required fields are present
    if required_fields:
        data = request.get_json()
        for field in required_fields:
            if field not in data:
                errors.append(f"'{field}' is required")
    
    return errors if errors else None
