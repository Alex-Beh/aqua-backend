import uuid

from app import db
from app.models import FishType
from app.models.fish_type import FishSize
from sqlalchemy.orm import defer
from contextlib import suppress

from app.utils import api_response, paginate_response
from app.utils.convert_images import normalize_image_to_jpeg
from app.services.supa_images import upload_image, delete_path


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
    def get_minimal(status=None):
        """Return only the small fields needed for selects / dashboards."""
        return (
            FishTypeService.base_query(status)
            # Skip the big binary columns
            .options(
                defer(FishType.image_data),
                defer(FishType.image_mime_type),
            )
            # Project only what you really need
            .with_entities(
                FishType.type_id,
                FishType.type_code,
                FishType.common_name,
                FishType.scientific_name,
            )
            .all()
        )

    @staticmethod
    def create(data, image_file=None, performed_by=None):
        validation_errors = FishTypeService.validate_fields(data)
        if validation_errors:
            return api_response("Validation errors occurred", errors=validation_errors, status_code=400)

        # Parse and validate size
        size = None
        if 'size' in data and data['size']:
            size = FishSize(data['size'])

        # Upload to Supabase Storage
        image_path = None
        type_code_ = FishTypeService.generate_type_code()

        if image_file and image_file.filename:
            try:
                stream, content_type, ext = normalize_image_to_jpeg(image_file)
                image_path = upload_image(
                    stream, content_type, type_code_, ext=ext)
            except Exception as e:
                return api_response("Unsupported or corrupt image format. Please try a different photo.", status_code=415)

        new_fish_type = FishType(
            type_code=type_code_,
            common_name=data.get('commonName'),
            scientific_name=data.get('scientificName'),
            size=size,
            image_path=image_path,
            is_active=data.get('isActive', 'true').lower() == 'true',
            created_at=db.func.current_timestamp(),
            created_by=performed_by
        )
        db.session.add(new_fish_type)
        db.session.commit()
        return api_response("Fish type created successfully", data=new_fish_type.to_dict(), status_code=201)

    @staticmethod
    def _validate_and_normalize_image(image_file):
        """
        Returns (stream, content_type, ext) when a valid file is supplied.
        If no file was sent, returns (None, None, None).

        Raises ValueError when the extension is not allowed.
        """
        if not image_file or not getattr(image_file, "filename", ""):
            # Nothing uploaded in this request
            return None, None, None

        if not FishTypeService.allowed_file(image_file.filename):
            raise ValueError(
                f"Unsupported extension. Allowed: {', '.join(FishTypeService.ALLOWED_EXTENSIONS)}"
            )

        # convert → RGB JPEG, keep original ext so we can store it
        return normalize_image_to_jpeg(image_file)

    @staticmethod
    def update(fish_type, data, image_file=None, performed_by=None):
        # ---- 2-a) field-level validation ------------------------------
        validation_errors = FishTypeService.validate_fields(data, for_update=True)
        if validation_errors:
            return api_response(
                "Validation errors occurred", errors=validation_errors, status_code=400
            )

        # ---- 2-b) image handling --------------------------------------
        try:
            stream, content_type, ext = FishTypeService._validate_and_normalize_image(image_file)
        except ValueError as exc:
            # bad extension or other validation issue
            return api_response(str(exc), status_code=415)

        if stream:  # A *new* image really was provided
            # Remove the old object if it exists (ignore errors silently)
            if fish_type.image_path:
                with suppress(Exception):
                    delete_path(fish_type.image_path)

            # Give each upload its own key to avoid collisions
            key = f"{fish_type.type_code}_{uuid.uuid4().hex[:8]}.{ext}"
            fish_type.image_path = upload_image(stream, content_type, key)

        # ---- 2-c) scalar / enum fields --------------------------------
        fish_type.common_name = data.get('commonName', fish_type.common_name)
        fish_type.scientific_name = data.get('scientificName', fish_type.scientific_name)

        if 'size' in data:
            fish_type.size = FishSize(data['size']) if data['size'] else None

        if 'isActive' in data:
            fish_type.is_active = str(data['isActive']).lower() == 'true'

        # ---- 2-d) audit metadata & commit -----------------------------
        fish_type.updated_at = db.func.current_timestamp()
        fish_type.updated_by = performed_by

        db.session.add(fish_type)   # harmless if already in session
        db.session.commit()

        return api_response(
            "Fish type updated successfully",
            data=fish_type.to_dict()
        )

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
