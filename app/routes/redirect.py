from flask import Blueprint, redirect, abort, current_app
from app import db
from app import config   # adjust if you use an app factory pattern

bp = Blueprint("redirect", __name__, url_prefix="/r")

@bp.route("/<code>")
def redirect_code(code: str):
    """Handle /r/<code> → real URL"""
    url = config.URL_MAP.get(code)
    if url:
        # 302 means “temporary” – change to 301 if you want it cached in browsers
        return redirect(url, code=302)
    return abort(404, description="QR code target not found")
