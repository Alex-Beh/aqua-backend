# /app/utils/api_response.py

from flask import jsonify

def api_response(
    message,
    data=None,
    errors=None,
    success=None,
    status_code=200
):
    """
    Standardized API response.

    :param message: A short message describing the outcome.
    :param data: Payload to return (optional).
    :param errors: Dict or list or string containing error details (optional).
    :param success: Auto-handled unless manually set.
    :param status_code: HTTP status code (default: 200)
    :return: JSON response with uniform structure.
    """
    # Auto-derive success if not set
    if success is None:
        success = status_code < 400

    response = {
        "success": success,
        "message": message,
        "data": data or {}
    }

    if errors:
        if isinstance(errors, dict):
            response["errors"] = errors
        elif isinstance(errors, list):
            response["errors"] = {"general": errors}
        else:
            response["errors"] = {"general": str(errors)}

    return jsonify(response), status_code
