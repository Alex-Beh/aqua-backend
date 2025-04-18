from flask import Blueprint, request, jsonify
from app import db
from app.models.tank import Tank
from datetime import datetime

bp = Blueprint('tanks', __name__, url_prefix='/api/tanks')

@bp.route('', methods=['GET'])
def get_all_tanks():
    tanks = Tank.query.filter_by(is_active=True).all()
    return jsonify([tank.to_dict() for tank in tanks])

@bp.route('/<int:tank_id>', methods=['GET'])
def get_tank(tank_id):
    tank = Tank.query.get_or_404(tank_id)
    if not tank.is_active:
        return jsonify({'error': 'Tank not found'}), 404
    return jsonify(tank.to_dict())

@bp.route('', methods=['POST'])
def create_tank():
    data = request.get_json()
    new_tank = Tank(
        site_id=data['siteId'],
        tank_name=data['tankName']
    )
    db.session.add(new_tank)
    db.session.commit()
    return jsonify(new_tank.to_dict()), 201

@bp.route('/<int:tank_id>', methods=['PUT'])
def update_tank(tank_id):
    tank = Tank.query.get_or_404(tank_id)
    data = request.get_json()
    tank.tank_name = data.get('tankName', tank.tank_name)
    tank.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(tank.to_dict())

@bp.route('/<int:tank_id>', methods=['DELETE'])
def delete_tank(tank_id):
    tank = Tank.query.get_or_404(tank_id)
    tank.is_active = False
    tank.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Tank deleted successfully'})
