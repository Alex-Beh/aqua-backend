import enum
from datetime import datetime

from app import db

from app.models.site import Site

class Tank(db.Model):
    """Physical tank that can contain multiple fish types."""
    __tablename__ = 'tanks'

    tank_id = db.Column(db.Integer, primary_key=True)
    tank_name = db.Column(db.String(100), nullable=False)
    tank_code = db.Column(db.String(20), unique=True, nullable=False)

    site_id = db.Column(db.Integer, db.ForeignKey("sites.site_id"), nullable=False)

    capacity = db.Column(db.Integer)
    size = db.Column(db.String(20), nullable=True) 
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
            'capacity': self.capacity if self.capacity else None,
            'size': self.size if self.size else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None,
            'status': self.status,
            'createdBy': self.created_by,
            'updatedBy': self.updated_by,
            'deletedBy': self.deleted_by
        }
    
    def to_dict_QR_Purpose(self):
        return {
            'tankId': self.tank_id,
            'tankName': self.tank_name,
            'tankCode': self.tank_code,
            'size': self.size if self.size else None,
        }
    
    def to_dict_dropdown(self):
        return {
            'tankId': self.tank_id,
            'tankName': self.tank_name,
            'tankCode': self.tank_code,
        }