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
    deleted_at = db.Column(db.DateTime)
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
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None,
            'isActive': self.is_active
        }
    
    # Soft delete logic
    def soft_delete(self, user_id=None):
        """Marks the record as deleted"""
        self.deleted_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        #self.deleted_by = user_id  # If tracking who deleted
        db.session.add(self)
        return self
        
    @classmethod
    def validate_fields(cls, data, for_update=False):
        """Unified validation returning consistent error format
        Returns:
            dict: {field: error_message} if errors, None if valid
        """
        errors = {}
        
        # Required fields validation
        if not for_update and not data.get('typeCode'):
            errors['typeCode'] = "Type Code is required"
        
        if not data.get('commonName'):
            errors['commonName'] = "Common Name is required"
        
        # Type code specific rules (only when provided or creating)
        if 'typeCode' in data or not for_update:
            type_code = data.get('typeCode', '').upper()
            
            if not for_update and not type_code:  # Already handled above
                pass
            elif len(type_code) < 3:
                errors['typeCode'] = "Type Code too short (min 3 chars)"
            elif cls.query.filter(db.func.upper(cls.type_code) == type_code).first():
                errors['typeCode'] = "Type Code already exists"
        
        return errors if errors else None