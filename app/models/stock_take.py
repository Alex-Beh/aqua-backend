from app import db
from datetime import datetime

class StockTake(db.Model):
    __tablename__ = 'stock_take'

    stock_take_id = db.Column(db.Integer, primary_key=True)
    tank_id = db.Column(db.Integer, db.ForeignKey('tanks.tank_id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.site_id'), nullable=False)

    initiate_by = db.Column(db.String(100))
    initiate_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    finalize_by = db.Column(db.String(100))
    finalize_at = db.Column(db.DateTime)

    remarks = db.Column(db.Text)
    review_comment = db.Column(db.Text)

    status = db.Column(db.String(20), default='Draft')  # Draft, Pending, Approve, Rejected, Cancelled

    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())

    # Relationships
    tank = db.relationship("Tank", backref="stock_takes")
    items = db.relationship("StockTakeItem", back_populates="stock_take", cascade="all, delete-orphan")

    # If need then can open
    # site = db.relationship("Site", backref="stock_takes")

    def to_dict(self):
        return {
            "stockTakeId": self.stock_take_id,
            "tankId": self.tank_id,
            "tank": self.tank.to_dict() if self.tank else None,
            "siteId": self.site_id,  # Include siteId in the response
            # "site": self.site.to_dict() if self.site else None,  # Include site details if needed
            'initiateBy': self.initiate_by,
            "initiateAt": self.initiate_at.isoformat() if self.initiate_at else None,
            'finalizeBy': self.finalize_by,
            "finalizeAt": self.finalize_at.isoformat() if self.finalize_at else None,
            "remarks": self.remarks,
            "reviewComment": self.review_comment,
            "status": self.status,
            'createdBy': self.created_by,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            'updatedBy': self.updated_by,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def is_stock_take_in_progress(cls, tank_id):
        """Check if there's an existing stock take under Draft or Pending status for the given tank."""
        return cls.query.filter_by(tank_id=tank_id).filter(cls.status.in_(['Draft', 'Pending'])).first() is not None
