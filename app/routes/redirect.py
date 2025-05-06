from flask import Blueprint, redirect, abort, current_app
from app import db
from app import config   # adjust if you use an app factory pattern
from app.utils import api_response

bp = Blueprint("redirect", __name__, url_prefix="/r")

@bp.route("/<code>")
def get_redirect_url(code: str):
    """Return the target URL for the given QR code in JSON payload"""
    url = config.URL_MAP.get(code)
    if url:
        print(f"{code} maps to: {url}")
        return api_response("Redirect URL retrieved", data={"url": url})
    return abort(404, description="QR code target not found")
