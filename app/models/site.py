from app import db
from datetime import datetime

# Site model
class Site(db.Model):
    __tablename__ = 'site'

    site_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.company_id'))
    site_name = db.Column(db.String(100), nullable=False)
    site_code = db.Column(db.String(50), unique=True, nullable=False)
    location = db.Column(db.String(200))
    hotline = db.Column(db.String(50))
    site_manager_id = db.Column(db.Integer)
    site_contact_id = db.Column(db.Integer)
    created_by = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime)
    deleted_by = db.Column(db.Integer)
    deleted_at = db.Column(db.DateTime)

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