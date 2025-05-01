from app import db
from datetime import datetime
from app.models.site import Site
from app.models.company import Company
from app.utils import api_response, paginate_response

class SiteService:

    @staticmethod
    def get_sites_paged(page, size, sort_field, sort_order, company_id=None):
        query = Site.query.filter(Site.deleted_at.is_(None))
        if company_id and company_id > 0:
            query = query.filter_by(company_id=company_id)
        return paginate_response(query, page, size, Site, sort_field, sort_order)

    @staticmethod
    def get_all_sites(company_id=None):
        query = Site.query.filter(Site.deleted_at.is_(None))
        if company_id and company_id > 0:
            query = query.filter_by(company_id=company_id)
        return [site.to_dict() for site in query.order_by(Site.site_name.asc()).all()]

    @staticmethod
    def get_site(site_id):
        site = Site.query.get(site_id)
        if not site or site.deleted_at:
            return None
        return site.to_dict()

    @staticmethod
    def create_site(data, performed_by=None):
        validation_errors = SiteService.validate_fields(data)
        if validation_errors:
            return api_response("Validation errors occurred", errors=validation_errors, status_code=400)

        new_site = Site(
            company_id=data.get('companyId'),
            site_name=data.get('siteName'),
            site_code=data.get('siteCode').upper(),
            location=data.get('location'),
            hotline=data.get('hotline'),
            site_manager_id=data.get('siteManagerId'),
            site_contact_id=data.get('siteContactId'),
            created_by=performed_by,
            created_at=db.func.current_timestamp()
        )

        db.session.add(new_site)
        db.session.commit()
        return api_response("Site created successfully", data=new_site.to_dict(), status_code=201)

    @staticmethod
    def update_site(site_id, data, performed_by=None):
        site = Site.query.get(site_id)
        if not site or site.deleted_at:
            return api_response("Site not found", status_code=404)

        validation_errors = SiteService.validate_fields(data, for_update=True)
        if validation_errors:
            return api_response("Validation errors occurred", errors=validation_errors, status_code=400)

        site.site_name = data.get('siteName', site.site_name)
        site.location = data.get('location', site.location)
        site.hotline = data.get('hotline', site.hotline)
        site.site_manager_id = data.get('siteManagerId', site.site_manager_id)
        site.site_contact_id = data.get('siteContactId', site.site_contact_id)
        site.updated_by = performed_by
        site.updated_at = db.func.current_timestamp()

        db.session.commit()
        return api_response("Site updated successfully", data=site.to_dict())

    @staticmethod
    def delete_site(site_id, performed_by=None):
        site = Site.query.get(site_id)
        if not site or site.deleted_at:
            return api_response("Site not found", status_code=404)

        if not SiteService.can_be_deleted(site):
            return api_response("Cannot delete: Site still has active tanks.", status_code=400)

        SiteService.soft_delete(site, performed_by=performed_by)
        db.session.commit()
        return api_response("Site deleted successfully")

    @staticmethod
    def validate_fields(data, for_update=False):
        errors = {}

        if not data.get('siteName'):
            errors['siteName'] = "Site Name is required"

        if not data.get('companyId'):
            errors['companyId'] = "Company ID is required"
        else:
            company_id = data['companyId']
            company = Company.query.filter_by(company_id=company_id, deleted_at=None).first()
            if not company:
                errors['companyId'] = "Invalid or deleted Company ID"

        if not for_update:
            if not data.get('siteCode'):
                errors['siteCode'] = "Site Code is required"
            else:
                site_code = data.get('siteCode', '').upper()
                if len(site_code) < 2:
                    errors['siteCode'] = "Site Code too short (min 2 chars)"
                elif Site.query.filter(db.func.upper(Site.site_code) == site_code).first():
                    errors['siteCode'] = "Site Code already exists"

        return errors if errors else None

    @staticmethod
    def can_be_deleted(site: Site):
        return all(tank.deleted_at is not None for tank in site.tanks)

    @staticmethod
    def soft_delete(site: Site, performed_by=None):
        site.updated_at = db.func.current_timestamp()
        site.deleted_at = db.func.current_timestamp()
        site.deleted_by = performed_by
        db.session.add(site)
