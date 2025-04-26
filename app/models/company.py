from app import db
from datetime import datetime

# Company model
class Company(db.Model):
    __tablename__ = 'company'

    company_id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    company_code = db.Column(db.String(50), unique=True, nullable=False)
    hotline = db.Column(db.String(50))
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    #created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    #updated_by = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    #deleted_by = db.Column(db.Integer)
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'companyId': self.company_id,
            'companyName': self.company_name,
            'companyCode': self.company_code,
            'hotline': self.hotline,
            'email': self.email,
            'address': self.address,
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
    
    @staticmethod
    def validate_fields(data, for_update=False):
        errors = []

        if not for_update:
            # For creation: both company name and code are required
            if not data.get('companyName'):
                errors.append('Company name is required')

            if not data.get('companyCode'):
                errors.append('Company code is required')
            else:
                existing = Company.query.filter_by(company_code=data.get('companyCode').upper()).first()
                if existing:
                    errors.append('Company code already exists')
        else:
            # For update: optionally require company name
            if not data.get('companyName'):
                errors.append('Company name is required')

        return errors
    
    def can_be_deleted(self):
        """Check if company can be deleted (no active sites attached)."""
        from app.models.site import Site  # Import here to avoid circular import

        active_sites = Site.query.filter(
            Site.company_id == self.company_id,
            Site.deleted_at.is_(None)
        ).count()

        return active_sites == 0
