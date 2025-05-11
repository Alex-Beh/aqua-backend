import base64
from app import db
from datetime import datetime
import enum

# Fish Size Enum
class FishSize(enum.Enum):
    SMALL = "small"
    MEDIUM = "medium"
    BIG = "big"

# Fish Type 
class FishType(db.Model):
    __tablename__ = 'fish_types'
    
    type_id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.String(20), unique=True, nullable=False)
    common_name = db.Column(db.String(100), nullable=False)
    scientific_name = db.Column(db.String(100))
    size = db.Column(db.Enum(FishSize), nullable=True)
    image_url = db.Column(db.String(255))
    image_data = db.Column(db.LargeBinary)
    image_mime_type = db.Column(db.String(50))
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    deleted_by = db.Column(db.String(100))
    deleted_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    stocks = db.relationship("TankStock", back_populates="fish_type", cascade="all, delete-orphan")

    def to_dict(self, include_image_data=False):
        data = {
            'typeId': self.type_id,
            'typeCode': self.type_code,
            'commonName': self.common_name,
            'scientificName': self.scientific_name,
            'size': self.size.value if self.size else None,
            'imageUrl': self.image_url,
            'isActive': self.is_active,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedBy': self.updated_by,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'deletedBy': self.deleted_by,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None
        }

        # Conditionally include base64 image data
        if include_image_data and self.image_data:
            data['imageData'] = base64.b64encode(self.image_data).decode('utf-8')
            data['imageMimeType'] = self.image_mime_type
            
        return data