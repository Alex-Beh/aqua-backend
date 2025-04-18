from app import db
from datetime import datetime

# Fish Type 
class FishType(db.Model):
    __tablename__ = 'fish_types'
    
    type_id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.String(20), unique=True, nullable=False)
    common_name = db.Column(db.String(100), nullable=False)
    scientific_name = db.Column(db.String(100))
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'typeId': self.type_id,
            'typeCode': self.type_code,
            'commonName': self.common_name,
            'scientificName': self.scientific_name,
            'imageUrl': self.image_url,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'isActive': self.is_active
        }