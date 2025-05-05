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
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    deleted_by = db.Column(db.String(100))
    deleted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'companyId': self.company_id,
            'companyName': self.company_name,
            'companyCode': self.company_code,
            'hotline': self.hotline,
            'email': self.email,
            'address': self.address,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedBy': self.updated_by,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'deletedBy': self.deleted_by,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None,
        }
    
    @staticmethod
    def validate_fields(data, for_update=False):
        errors = {}

        return errors if errors else None

    def __repr__(self):
        return f"<Company {self.company_code}>"
