import enum
from datetime import datetime

from app import db

from app.models.site import Site

class CapacityEnum(enum.Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    BIG = "BIG"

class Tank(db.Model):
    """Physical tank that can contain multiple fish types."""
    __tablename__ = 'tanks'

    tank_id = db.Column(db.Integer, primary_key=True)
    tank_name = db.Column(db.String(100), nullable=False)
    tank_code = db.Column(db.String(20), unique=True, nullable=False)

    site_id = db.Column(db.Integer, db.ForeignKey("sites.site_id"), nullable=False)
    site = db.relationship('Site', backref='tanks')

    capacity = db.Column(db.Enum(CapacityEnum), nullable=False)
    image = db.Column(db.LargeBinary)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    deleted_by = db.Column(db.String(100))
    deleted_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Active')

    # Relationships
    site = db.relationship("Site", back_populates="tanks")
    stocks = db.relationship(
        "TankStock", back_populates="tank", cascade="all, delete-orphan"
    )

    # Helpers -----------------------------------------------------------------
    def to_dict(self):
        return {
            'tankId': self.tank_id,
            "site": self.site.to_dict() if self.site else None,  # 👈 include nested site
            'siteId': self.site_id,
            'tankName': self.tank_name,
            'tankCode': self.tank_code,
            'capacity': self.capacity.value if self.capacity else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None,
            'status': self.status,
            'createdBy': self.created_by,
            'updatedBy': self.updated_by,
            'deletedBy': self.deleted_by
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
    def validate_fields(cls, data, for_update=False, is_batch=False):
        errors = {}

        if not data.get('siteId'):
            errors['siteId'] = "Site ID is required"
        else:
            site = Site.query.filter_by(site_id=data['siteId'], deleted_at=None).first()
            if not site:
                errors['siteId'] = "Invalid or deleted Site ID"

        if not is_batch:
            if not data.get('tankName'):
                errors['tankName'] = "Tank Name is required"

        # Validate status
        status = data.get('status')
        if not status:
            errors['status'] = "Status is required"
        elif status not in ['active', 'maintenance', 'retired']:
            errors['status'] = "Invalid status value"

        # Capacity validation if provided
        if 'capacity' in data and data['capacity'] is not None:
            try:
                CapacityEnum(data['capacity'])
            except ValueError:
                errors['capacity'] = f"Capacity must be one of: {', '.join([c.value for c in CapacityEnum])}"

        return errors if errors else None

    @classmethod
    def generate_auto_code(cls, site_id):
        site = Site.query.get(site_id)
        
        if not site:
            raise ValueError("Invalid site ID provided.")
        
        site_code = site.site_code.upper() if site.site_code else 'UNKNOWN'

        # Ensure that no duplicate tank codes exist for this site
        existing_count = cls.query.filter_by(site_id=site_id).count()
        
        if existing_count > 999:
            raise ValueError("Maximum tank limit reached for this site.")
        
        next_number = existing_count + 1
        return f"T-{site_code}-{str(next_number).zfill(3)}"

    def can_be_deleted(self):
        """Check if the tank has no stock left (safe to delete)."""
        for stock in self.stocks:
            if stock.quantity > 0:
                return False
        return True
