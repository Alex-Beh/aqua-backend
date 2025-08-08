import base64
from app import db
import enum
from app.services.supa_images import public_url, thumb_url


class FishSize(enum.Enum):
    SMALL = "small"
    MEDIUM = "medium"
    BIG = "big"


class FishType(db.Model):
    __tablename__ = 'fish_types'

    type_id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.String(20), unique=True, nullable=False)
    common_name = db.Column(db.String(100), nullable=False)
    scientific_name = db.Column(db.String(100))
    size = db.Column(db.Enum(FishSize), nullable=True)

    # (source of truth going forward)
    image_path = db.Column(db.String(512))

    # LEGACY (to remove after backfill) # deprecated
    image_url = db.Column(db.String(255))
    image_data = db.Column(db.LargeBinary)
    image_mime_type = db.Column(db.String(50))

    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    deleted_by = db.Column(db.String(100))
    deleted_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    stocks = db.relationship(
        "TankStock", back_populates="fish_type", cascade="all, delete-orphan")

    def to_dict(self, include_image_data=False):
        data = {
            'typeId': self.type_id,
            'typeCode': self.type_code,
            'commonName': self.common_name,
            'scientificName': self.scientific_name,
            'size': self.size.value if self.size else None,
            'imagePath': self.image_path,
            'isActive': self.is_active,
            'createdBy': self.created_by,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedBy': self.updated_by,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'deletedBy': self.deleted_by,
            'deletedAt': self.deleted_at.isoformat() if self.deleted_at else None
        }
        data.update(self._image_urls())

        # Conditionally include base64 image data
        if include_image_data and self.image_data:
            data['imageData'] = base64.b64encode(
                self.image_data).decode('utf-8')
            data['imageMimeType'] = self.image_mime_type

        return data

    def to_dict_QR_Purpose(self, include_image_data=False):
        data = {
            'typeId': self.type_id,
            'typeCode': self.type_code,
            'commonName': self.common_name,
            'scientificName': self.scientific_name,
            'size': self.size.value if self.size else None,
            'imagePath': self.image_path,
        }
        data.update(self._image_urls())

        # Conditionally include base64 image data
        if include_image_data and self.image_data:
            data['imageData'] = base64.b64encode(
                self.image_data).decode('utf-8')
            data['imageMimeType'] = self.image_mime_type

        return data

    def to_dict_dropdown(self):
        data = {
            'typeId': self.type_id,
            'typeCode': self.type_code,
            'commonName': self.common_name,
            'scientificName': self.scientific_name
        }

        return data

    # ---- helpers -------------------------------------------------------------
    def _image_urls(self):
        """
        Returns a dict of URLs derived from image_path (preferred),
        falling back to legacy image_url if needed.
        """
        if not self.image_path:
            return {}
        return {
            "imageUrl":  public_url(self.image_path),
            "thumb320": thumb_url(self.image_path, 320),
            "thumb480": thumb_url(self.image_path, 480),
        }
        return {}
