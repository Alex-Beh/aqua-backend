from app import db
from datetime import datetime

from app.models.company import Company

# Site model
class Site(db.Model):
    __tablename__ = "sites"

    site_id = db.Column(db.Integer, primary_key=True)
    # Optional FK to a future `company` table. Keep nullable=True for now so
    # we don't need that table immediately.
    company_id = db.Column(db.Integer, nullable=True)

    site_name = db.Column(db.String(100), nullable=False)
    site_code = db.Column(db.String(50), unique=True, nullable=False)
    location = db.Column(db.String(200))
    hotline = db.Column(db.String(50))

    site_manager_id = db.Column(db.Integer)  # FK to user table (optional)
    site_contact_id = db.Column(db.Integer)  # FK to user table (optional)

    created_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    deleted_by = db.Column(db.Integer)
    deleted_at = db.Column(db.DateTime)

    is_active = db.Column(db.Boolean, default=True)

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
            #'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            #'updatedBy': self.updated_by,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            #'deletedBy': self.deleted_by,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None,
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

        # Required fields
        if not data.get('siteName'):
            errors['siteName'] = "Site Name is required"

        if not data.get('companyId'):
            errors['companyId'] = "Company ID is required"

        # Validate the companyId on creation and update
        company_id = data.get('companyId')
        company = Company.query.filter_by(company_id=company_id, deleted_at=None).first()
        if not company:
            errors['companyId'] = "Invalid or deleted Company ID"

        # Only validate siteCode on creation
        if not for_update:
            if not data.get('siteCode'):
                errors['siteCode'] = "Site Code is required"
            else:
                site_code = data.get('siteCode', '').upper()
                if len(site_code) < 2:
                    errors['siteCode'] = "Site Code too short (min 2 chars)"
                elif cls.query.filter(db.func.upper(cls.site_code) == site_code).first():
                    errors['siteCode'] = "Site Code already exists"

        return errors if errors else None

    def can_be_deleted(self):
        """Check if site can be deleted (no active tanks attached)."""
        active_tanks = [tank for tank in self.tanks if tank.deleted_at is None]
        return len(active_tanks) == 0
