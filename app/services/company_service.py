from flask_login import current_user
from app import db
from app.models import Company
from app.models.site import Site
from app.utils import api_response, paginate_response
from datetime import datetime

class CompanyService:
    
    @staticmethod
    def get_companies_paged(page, size, sort_field, sort_order):
        query = Company.query.filter(Company.deleted_at.is_(None))
        return paginate_response(query, page, size, Company, sort_field, sort_order)

    @staticmethod
    def get_all_companies():
        items = Company.query.filter(Company.deleted_at.is_(None)).all()
        return [c.to_dict() for c in items]

    @staticmethod
    def get_sites_paged(company_id, page, size, sort_field, sort_order):
        query = Site.query.filter(Site.company_id == company_id, Site.deleted_at.is_(None))
        return paginate_response(query, page, size, Site, sort_field, sort_order)

    @staticmethod
    def get_all_sites(company_id):
        sites = Site.query.filter(Site.company_id == company_id, Site.deleted_at.is_(None)).all()
        return [s.to_dict() for s in sites]

    @staticmethod
    def get_company(company_id):
        company = Company.query.get(company_id)
        if not company or company.deleted_at:
            return None
        return company.to_dict()

    @staticmethod
    def create_company(data, user_id):
        validation_errors = Company.validate_fields(data)
        if validation_errors:
            return api_response("Validation errors occurred", errors=validation_errors, status_code=400)

        new_company = Company(
            company_name=data.get('companyName'),
            company_code=data.get('companyCode').upper(),
            hotline=data.get('hotline'),
            email=data.get('email'),
            address=data.get('address'),
            created_by=user_id
        )
        db.session.add(new_company)
        db.session.commit()
        return api_response("Company created successfully", data=new_company.to_dict(), status_code=201)
    
    @staticmethod
    def update_company(company_id, data):
        company = Company.query.get(company_id)
        if not company or company.deleted_at:
            return api_response("Company not found", status_code=404)

        validation_errors = Company.validate_fields(data, for_update=True)
        if validation_errors:
            return api_response("Validation errors occurred", errors=validation_errors, status_code=400)

        company.company_name = data.get('companyName', company.company_name)
        company.hotline = data.get('hotline', company.hotline)
        company.email = data.get('email', company.email)
        company.address = data.get('address', company.address)
        company.updated_by = current_user.id
        db.session.commit()
        return api_response("Company updated successfully", data=company.to_dict())
    
    @staticmethod
    def delete_company(company_id, user_id):
        company = Company.query.get(company_id)
        if not company or company.deleted_at:
            return api_response("Company not found", status_code=404)

        # Check if the company can be deleted
        if not CompanyService.can_be_deleted(company):
            return api_response("Cannot delete: Company still has active sites.", status_code=400)

        # Perform soft delete logic
        company.deleted_at = db.func.current_timestamp()
        if user_id:
            company.deleted_by = user_id
        db.session.add(company)
        db.session.commit()

        return api_response("Company deleted successfully")

    @staticmethod
    def can_be_deleted(company):
        """Check if company can be deleted (no active sites attached)."""
        active_sites = Site.query.filter(
            Site.company_id == company.company_id,
            Site.deleted_at.is_(None)
        ).count()

        return active_sites == 0
    
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