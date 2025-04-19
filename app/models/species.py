from app import db
from datetime import datetime

class Species(db.Model):
    """Reference table for fish species (a.k.a. fish types)."""

    __tablename__ = "species"

    species_id = db.Column(db.Integer, primary_key=True)
    common_name = db.Column(db.String(100), nullable=False)
    scientific_name = db.Column(db.String(255))
    notes = db.Column(db.Text)
    image = db.Column(db.LargeBinary)  # Optional species image

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    stocks = db.relationship(
        "TankStock", back_populates="species", cascade="all, delete-orphan"
    )

    # Helpers -----------------------------------------------------------------
    def to_dict(self):
        return {
            "speciesId": self.species_id,
            "commonName": self.common_name,
            "scientificName": self.scientific_name,
            "notes": self.notes,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }