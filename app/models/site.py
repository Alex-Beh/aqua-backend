from app import db
from datetime import datetime

from app.models.company import Company

# Site model
class Site(db.Model):
    __tablename__ = "sites"

    site_id = db.Column(db.Integer, primary_key=True)
    # Optional FK to a future `company` table. Keep nullable=True for now so
    company_id = db.Column(db.Integer, nullable=True)

    site_name = db.Column(db.String(100), nullable=False)
    site_code = db.Column(db.String(50), unique=True, nullable=False)
    location = db.Column(db.String(200))
    hotline = db.Column(db.String(50))

    site_manager_id = db.Column(db.Integer)  # FK to user table (optional)
    site_contact_id = db.Column(db.Integer)  # FK to user table (optional)
    is_active = db.Column(db.Boolean, default=True)

    created_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    deleted_by = db.Column(db.Integer)
    deleted_at = db.Column(db.DateTime)

    # Relationships -----------------------------------------------------------
    tanks = db.relationship(
        "Tank",
        back_populates="site",
        cascade="all, delete-orphan",
        lazy=True,
    )

    # -------------------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Site {self.site_code}>"

    def to_dict(self):
        return {
            'siteId': self.site_id,
            'companyId': self.company_id,
            'siteName': self.site_name,
            'siteCode': self.site_code,
            'location': self.location,
            'hotline': self.hotline,
            'siteManagerId': self.site_manager_id,
            'siteContactId': self.site_contact_id,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedBy': self.updated_by,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'deletedBy': self.deleted_by,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None,
        }