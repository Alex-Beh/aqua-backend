
from flask import Blueprint, request, jsonify
from app.models import Species
from app import db
from datetime import datetime


def _serialize_species(sp: Species) -> dict:
    return sp.to_dict()


# ---------------------------------------------------------------------------
# Species endpoints ---------------------------------------------------------
# ---------------------------------------------------------------------------
species_bp = Blueprint("species_bp", __name__, url_prefix="/api/species")


@species_bp.route("", methods=["GET"])
def list_species():
    include_inactive = request.args.get(
        "includeInactive", "false").lower() == "true"
    q = Species.query
    if not include_inactive:
        q = q.filter_by(is_active=True)
    return jsonify([_serialize_species(s) for s in q.all()])


@species_bp.route("/<int:species_id>", methods=["GET"])
def get_species(species_id):
    sp = Species.query.get_or_404(species_id)
    return jsonify(_serialize_species(sp))


@species_bp.route("", methods=["POST"])
def create_species():
    data = request.get_json(force=True)
    sp = Species(
        common_name=data["commonName"],
        scientific_name=data.get("scientificName"),
        notes=data.get("notes"),
    )
    db.session.add(sp)
    db.session.commit()
    return jsonify(_serialize_species(sp)), 201


@species_bp.route("/<int:species_id>", methods=["PUT"])
def update_species(species_id):
    sp = Species.query.get_or_404(species_id)
    data = request.get_json(force=True)
    sp.common_name = data.get("commonName", sp.common_name)
    sp.scientific_name = data.get("scientificName", sp.scientific_name)
    sp.notes = data.get("notes", sp.notes)
    sp.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_serialize_species(sp))


@species_bp.route("/<int:species_id>", methods=["DELETE"])
def soft_delete_species(species_id):
    sp = Species.query.get_or_404(species_id)
    sp.is_active = False
    sp.deleted_at = datetime.utcnow()
    db.session.commit()
    return "", 204
