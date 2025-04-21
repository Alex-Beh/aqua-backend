from app import db
from datetime import datetime

class StockTakeItem(db.Model):
    __tablename__ = 'stock_take_item'

    stock_take_item_id = db.Column(db.Integer, primary_key=True)
    stock_take_id = db.Column(db.Integer, db.ForeignKey('stock_take.stock_take_id'), nullable=False)
    fish_type_id = db.Column(db.Integer, db.ForeignKey('fish_types.type_id'), nullable=False)

    expected_quantity = db.Column(db.Integer, nullable=False)
    counted_quantity = db.Column(db.Integer, nullable=False)
    
    # adjustment_id as a simple integer, can be 0 if no adjustment
    adjustment_id = db.Column(db.Integer, nullable=True, default=0)

    # Relationships
    stock_take = db.relationship("StockTake", back_populates="items")
    fish_type = db.relationship("FishType", lazy='joined')

    @property
    def adjustment_quantity(self):
        return self.counted_quantity - self.expected_quantity

    def to_dict(self):
        return {
            "stockTakeItemId": self.stock_take_item_id,
            "stockTakeId": self.stock_take_id,
            "fishTypeId": self.fish_type_id,
            "fishType": self.fish_type.to_dict() if self.fish_type else None,
            "expectedQuantity": self.expected_quantity,
            "countedQuantity": self.counted_quantity,
            "adjustmentQuantity": self.adjustment_quantity,
            "adjustmentId": self.adjustment_id,
        }
