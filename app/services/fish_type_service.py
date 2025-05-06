from app import db
from app.models import FishType
from app.models.fish_type import FishSize
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from app.utils import api_response, paginate_response

class FishTypeService:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    @staticmethod
    def base_query(status=None):
        query = FishType.query.filter(FishType.deleted_at.is_(None))
        if status == 'active':
            query = query.filter(FishType.is_active.is_(True))
        elif status == 'inactive':
            query = query.filter(FishType.is_active.is_(False))
        return query
    
    @staticmethod
    def get_paginated(page, size, status=None, sort_field='type_code', sort_order='asc'):
        query = FishTypeService.base_query(status)
        return paginate_response(query, page, size, FishType, sort_field, sort_order, include_image_data=True)

    @staticmethod
    def get_all(status=None):
        return FishTypeService.base_query(status).all()

    @staticmethod
    def get_query(status=None):
        return FishTypeService.base_query(status)

    @staticmethod
    def get_by_id(type_id):
        return FishType.query.get(type_id)

    @staticmethod
    def create(data, image_file=None, upload_folder=None, performed_by=None):
        validation_errors = FishTypeService.validate_fields(data)
        if validation_errors:
            return api_response("Validation errors occurred", errors=validation_errors, status_code=400)

        # Parse and validate size
        size = None
        if 'size' in data and data['size']:
            size = FishSize(data['size'])

        # Handle image and store as binary data
        image_data = None
        image_mime_type = None
        if image_file and FishTypeService.allowed_file(image_file.filename):
            image_data = image_file.read()
            image_mime_type = image_file.mimetype

        type_code_ = FishTypeService.generate_type_code()
        new_fish_type = FishType(
            type_code=type_code_,
            common_name=data.get('commonName'),
            scientific_name=data.get('scientificName'),
            size=size,
            image_url=f"/uploads/fish_images/{type_code_}",
            image_data=image_data,
            image_mime_type=image_mime_type,
            is_active=data.get('isActive', 'true').lower() == 'true',
            created_at=db.func.current_timestamp(),
            created_by=performed_by
        )
        db.session.add(new_fish_type)
        db.session.commit()
        return api_response("Fish type created successfully", data=new_fish_type.to_dict(), status_code=201)

    @staticmethod
    def update(fish_type, data, image_file=None, upload_folder=None, performed_by=None):
        validation_errors = FishTypeService.validate_fields(data, for_update=True)
        if validation_errors:
            return api_response("Validation errors occurred", errors=validation_errors, status_code=400)

        if image_file and FishTypeService.allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            image_file.save(os.path.join(upload_folder, filename))
            fish_type.image_url = f"/uploads/fish_images/{filename}"

        fish_type.common_name = data.get('commonName', fish_type.common_name)
        fish_type.scientific_name = data.get('scientificName', fish_type.scientific_name)
        fish_type.is_active = data.get('isActive', str(fish_type.is_active)).lower() == 'true'

        if 'size' in data:
            fish_type.size = FishSize(data['size']) if data['size'] else None

        fish_type.updated_at = db.func.current_timestamp()
        fish_type.updated_by = performed_by
        db.session.commit()
        return api_response("Fish type updated successfully", data=fish_type.to_dict())

    @staticmethod
    def delete(type_id, performed_by=None):
        fish_type = FishType.query.get(type_id)

        # Check if fish type exists and not already deleted
        if not fish_type or fish_type.deleted_at:
            return api_response("Fish type not found", status_code=404)

        # Check if can be deleted
        if not FishTypeService.can_be_deleted(fish_type):
            return api_response("Cannot delete: Fish type still has stock in tanks.", status_code=400)

        # Soft delete
        FishTypeService.soft_delete(fish_type, performed_by)
        db.session.commit()

        return api_response("Fish type deleted successfully")
    
    @staticmethod
    def soft_delete(fish_type, performed_by=None):
        fish_type.deleted_at = db.func.current_timestamp()
        fish_type.updated_at = db.func.current_timestamp()
        fish_type.deleted_by = performed_by
        db.session.add(fish_type)

    @staticmethod
    def can_be_deleted(fish_type):
        """Check if the fish type has no stock left (safe to delete)."""
        for stock in fish_type.stocks:
            if stock.quantity > 0:
                return False
        return True

    @staticmethod
    def validate_fields(data, for_update=False):
        errors = {}

        if not data.get('commonName'):
            errors['commonName'] = "Common Name is required"

        if 'size' in data and data['size'] is not None:
            try:
                FishSize(data['size'])
            except ValueError:
                errors['size'] = f"Size must be one of: {', '.join([s.value for s in FishSize])}"

        return errors if errors else None

    @staticmethod
    def generate_type_code():
        prefix = 'FISH'
        existing_count = FishType.query.count()
        next_number = existing_count + 1
        return f"{prefix}-{str(next_number).zfill(4)}"

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in FishTypeService.ALLOWED_EXTENSIONS
