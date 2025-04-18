from app import db
from datetime import datetime

class Tank(db.Model):
    __tablename__ = 'tanks'

    tank_id = db.Column(db.Integer, primary_key=True) 
    tank_name = db.Column(db.String(100), nullable=False) # <---  pass from user
    tank_code = db.Column(db.String(20), unique=True, nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.site_id'), nullable=False)
    capacity = db.Column(db.Integer)
    image = db.Column(db.LargeBinary)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'tankId': self.tank_id,
            'siteId': self.site_id,
            'tankName': self.tank_name,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None,
            'isActive': self.is_active
        }
