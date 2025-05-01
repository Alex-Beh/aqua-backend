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
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    deleted_by = db.Column(db.String(100))
    deleted_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    stocks = db.relationship("TankStock", back_populates="fish_type", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'typeId': self.type_id,
            'typeCode': self.type_code,
            'commonName': self.common_name,
            'scientificName': self.scientific_name,
            'size': self.size.value if self.size else None,
            'imageUrl': self.image_url,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None,
            'isActive': self.is_active
        }
    
    # Soft delete logic
    def soft_delete(self, user_id=None):
        """Marks the record as deleted"""
        self.deleted_at = db.func.current_timestamp()
        self.updated_at = db.func.current_timestamp()
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
        if not data.get('commonName'):
            errors['commonName'] = "Common Name is required"
        
        # Size validation if provided
        if 'size' in data and data['size'] is not None:
            try:
                FishSize(data['size'])
            except ValueError:
                errors['size'] = f"Size must be one of: {', '.join([s.value for s in FishSize])}"
                
        return errors if errors else None
    
    @classmethod
    def generate_type_code(cls):
        prefix = 'FISH'
        existing_count = cls.query.count()  # Count all, including soft-deleted
        next_number = existing_count + 1
        return f"{prefix}-{str(next_number).zfill(4)}"
    
    def can_be_deleted(self):
        """Check if the fish type has no stock left (safe to delete)."""
        for stock in self.stocks:
            if stock.quantity > 0:
                return False
        return True
