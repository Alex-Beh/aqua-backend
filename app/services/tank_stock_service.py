from app import db
from app.models import TankStock, Tank, StockTake, StockTakeItem, FishType
from sqlalchemy.orm import joinedload
from app.utils import paginate_response
from sqlalchemy import or_, cast, String, desc
from datetime import datetime

class TankStockService:

    @staticmethod
    def get_all_tank_stock(tank_id=None, fish_type_id=None, site_id=None, search_text=""):
        """Fetches all tank stock with filters applied."""
        query = TankStock.query.options(
            joinedload(TankStock.tank),
            joinedload(TankStock.fish_type)
        ).join(Tank).join(FishType)

        # Apply filters
        query = TankStockService.apply_filters(query, tank_id, fish_type_id, site_id, search_text)
        
        # If tank_id and fish_type_id are provided, return only the first match (i.e., a single record)
        if tank_id and fish_type_id:
            return query.filter(TankStock.tank_id == tank_id, TankStock.fish_type_id == fish_type_id).first()

        return query

    @staticmethod
    def apply_filters(query, tank_id=None, fish_type_id=None, site_id=None, search_text=""):
        """Applies various filters to the query."""
        if tank_id and tank_id > 0:
            query = query.filter(TankStock.tank_id == tank_id)
        if fish_type_id and fish_type_id > 0:
            query = query.filter(TankStock.fish_type_id == fish_type_id)
        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)
        if search_text:
            search_lower = f"%{search_text.lower()}%"
            query = query.filter(
                db.or_(
                    db.func.lower(Tank.tank_name).like(search_lower),
                    db.func.lower(FishType.common_name).like(search_lower),
                    db.func.lower(FishType.type_code).like(search_lower),
                    cast(TankStock.quantity, String).like(search_lower)
                )
            )
        return query

    @staticmethod
    def get_paged_tank_stock(page, size, sort_field, sort_order, tank_id=None, fish_type_id=None, site_id=None, search_text=""):
        """Handles pagination and sorting for tank stock records."""
        
        # Get the base query with filters applied
        query = TankStockService.get_all_tank_stock(tank_id, fish_type_id, site_id, search_text)
        
        # Sorting logic
        valid_sort_fields = ["tank_name", "common_name", "quantity", "type_code"]
        if sort_field not in valid_sort_fields:
            sort_field = "tank_name"
        
        sort_mapping = {
            "tank_name": Tank.tank_name,
            "common_name": FishType.common_name,
            "quantity": TankStock.quantity,
            "type_code": FishType.type_code
        }

        sort_column = sort_mapping.get(sort_field, Tank.tank_name)
        query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column)

        return paginate_response(query, page, size, sort_order)

    @staticmethod
    def get_stock_summary(site_id=None):
        """Fetch total stock quantity per tank with optional site filter."""
        query = db.session.query(
            TankStock.tank_id,
            db.func.sum(TankStock.quantity).label("total_quantity")
        ).group_by(TankStock.tank_id).join(Tank)

        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)

        return query.all()

    @staticmethod
    def get_top_tanks_by_quantity(limit, site_id=None):
        """Fetch top tanks by total quantity of fish."""
        query = db.session.query(
            TankStock.tank_id,
            db.func.sum(TankStock.quantity).label("total_quantity")
        ).group_by(TankStock.tank_id) \
         .join(Tank) \
         .order_by(db.desc("total_quantity"))

        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)

        return query.limit(limit).all()

    @staticmethod
    def get_low_stock(threshold=10, status=None, site_id=None):
        """Fetches tank stock entries below the specified threshold and optionally filter by status."""
        query = TankStock.query.filter(TankStock.quantity < threshold).join(Tank).join(FishType)
        
        # If status is provided, filter by it
        if status:
            query = query.filter(Tank.status.lower() == status.lower())
        
        # If site_id is provided, filter by it
        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)

        query = query.order_by(Tank.tank_name)
        return query.all()

    @staticmethod
    def get_total_quantity_by_fish_type(fish_type_id):
        """Fetches the total quantity of a specific fish type across all tanks."""
        # Query to get the total quantity of the fish type
        total_quantity = db.session.query(db.func.sum(TankStock.quantity)) \
            .filter(TankStock.fish_type_id == fish_type_id) \
            .scalar()

        return total_quantity

    @staticmethod
    def get_total_quantity_per_tank(site_id=None):
        """Fetches the total quantity of fish for each tank, with optional site filter."""
        query = db.session.query(
            TankStock.tank_id,
            db.func.sum(TankStock.quantity).label("total_quantity")
        ).group_by(TankStock.tank_id).join(Tank)

        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)

        return query.all()

    @staticmethod
    def get_top_tanks_by_quantity(limit, site_id=None):
        """Fetches the top tanks by total quantity of fish."""
        query = db.session.query(
            TankStock.tank_id,
            db.func.sum(TankStock.quantity).label("total_quantity")
        ).group_by(TankStock.tank_id) \
         .join(Tank) \
         .order_by(db.desc("total_quantity"))

        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)

        return query.limit(limit).all()

    @staticmethod
    def get_site_distribution(site_id=None):
        """Fetches the distribution of tanks and fish types for each site."""
        query = db.session.query(
            Tank.site_id,
            db.func.count(db.func.distinct(Tank.tank_id)).label("tank_count"),
            db.func.count(db.func.distinct(FishType.type_id)).label("fish_type_count"),
            db.func.sum(TankStock.quantity).label("total_fish_count")
        ).join(TankStock, TankStock.tank_id == Tank.tank_id, isouter=True) \
        .join(FishType, TankStock.fish_type_id == FishType.type_id, isouter=True) \
        .group_by(Tank.site_id)

        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)

        return query.all()
    
    @staticmethod
    def build_tank_details(tank_id, total_quantity, tank_obj, include_fish_details: bool = True):
        fish_quantities = db.session.query(
            TankStock.fish_type_id,
            db.func.sum(TankStock.quantity).label("fish_total_quantity")
        ).filter(TankStock.tank_id == tank_id) \
         .group_by(TankStock.fish_type_id) \
         .join(FishType).all()

        fish_type_count = len(fish_quantities)

        fish_details = []
        if include_fish_details:
            for fish_type_id, fish_total_quantity in fish_quantities:
                fish_type = FishType.query.get(fish_type_id)
                if fish_type:
                    fish_details.append({
                        "fishTypeId": fish_type_id,
                        "commonName": fish_type.common_name,
                        "scientificName": fish_type.scientific_name,
                        "fishTotalQuantity": fish_total_quantity,
                        "createdAt": fish_type.created_at.isoformat() if fish_type.created_at else None,
                        "updatedAt": fish_type.updated_at.isoformat() if fish_type.updated_at else None,
                    })

        capacity = max(tank_obj.capacity or 0, 1)
        filled_percentage = round((total_quantity / capacity) * 100, 2)

        site = tank_obj.site

        return {
            "tankId": tank_obj.tank_id,
            "tankName": tank_obj.tank_name,
            "tankCode": tank_obj.tank_code,
            "status": tank_obj.status,
            "size": tank_obj.size,
            "totalTankCapacity": capacity,
            "totalFishCount": total_quantity,
            "tankFilledPercentage": filled_percentage,
            "fishTypeCount": fish_type_count,
            "fishDetails": fish_details,
            "siteId": site.site_id if site else None,
            "siteName": site.site_name if site else None,
            "siteCode": site.site_code if site else None,
        }
    
    @staticmethod
    def build_fish_inventory_query(site_id=None, tank_id=None, fish_type_id=None, search_text=None):
        query = db.session.query(
            FishType.type_id,
            FishType.common_name,
            FishType.type_code,
            FishType.scientific_name,
            db.func.count(TankStock.tank_id.distinct()).label("tank_count"),
            db.func.sum(TankStock.quantity).label("total_stock")
        ).join(TankStock, TankStock.fish_type_id == FishType.type_id)

        if tank_id and tank_id > 0:
            query = query.filter(TankStock.tank_id == tank_id)

        if fish_type_id and fish_type_id > 0:
            query = query.filter(TankStock.fish_type_id == fish_type_id)

        if site_id and site_id > 0:
            query = query.join(Tank, Tank.tank_id == TankStock.tank_id).filter(Tank.site_id == site_id)

        if search_text:
            search_lower = f"%{search_text.lower()}%"
            query = query.filter(
                db.or_(
                    db.func.lower(FishType.common_name).like(search_lower),
                    db.func.lower(FishType.type_code).like(search_lower),
                    db.func.lower(FishType.scientific_name).like(search_lower)
                )
            )

        return query.group_by(
            FishType.type_id,
            FishType.common_name,
            FishType.type_code,
            FishType.scientific_name
        )
    
    @staticmethod
    def get_fish_stats(site_id=None):
        query = db.session.query(db.func.sum(TankStock.quantity))
        tank_query = db.session.query(db.func.count(db.distinct(TankStock.tank_id)))

        if site_id and site_id > 0:
            query = query.join(Tank, Tank.tank_id == TankStock.tank_id).filter(Tank.site_id == site_id)
            tank_query = tank_query.join(Tank, Tank.tank_id == TankStock.tank_id).filter(Tank.site_id == site_id)

        total_fish = query.scalar() or 0
        tank_count = tank_query.scalar() or 0

        return total_fish, tank_count

    @staticmethod
    def get_active_tank_count(site_id=None):
        query = db.session.query(db.func.count(Tank.tank_id)).filter(
            db.func.lower(Tank.status) == "active",
            Tank.deleted_at.is_(None)
        )
        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)
        return query.scalar() or 0

    @staticmethod
    def get_fish_type_count(site_id=None):
        query = db.session.query(db.func.count(db.distinct(TankStock.fish_type_id))).join(Tank, Tank.tank_id == TankStock.tank_id)
        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)
        return query.scalar() or 0

    @staticmethod
    def get_tank_utilization(site_id=None):
        query = db.session.query(
            Tank.tank_id,
            db.func.sum(TankStock.quantity).label("total_quantity"),
            Tank.capacity
        ).join(TankStock, Tank.tank_id == TankStock.tank_id)

        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)

        query = query.filter(TankStock.quantity > 0)
        tank_data = query.group_by(Tank.tank_id, Tank.capacity).all()

        stocked_count = len(tank_data)
        total_capacity = sum(tank.capacity or 0 for tank in tank_data)
        total_quantity = sum(tank.total_quantity or 0 for tank in tank_data)

        total_tank_count = db.session.query(Tank).filter(
            Tank.site_id == site_id if site_id else True
        ).count()

        utilization = (stocked_count / total_tank_count * 100) if total_tank_count > 0 else 0
        capacity_utilization = (total_quantity / total_capacity * 100) if total_capacity > 0 else 0

        return {
            "count": stocked_count,
            "utilizationPercent": round(utilization, 1),
            "capacityUtilizationPercent": round(capacity_utilization, 1)
        }

    @staticmethod
    def get_last_stock_take(site_id=None):
        query = db.session.query(StockTake).filter(
            StockTake.status == "Approved",
            StockTake.finalize_at.isnot(None)
        )
        if site_id and site_id > 0:
            query = query.filter(StockTake.site_id == site_id)

        last_stock_take = query.order_by(desc(StockTake.finalize_at)).first()
        if last_stock_take:
            item_count = db.session.query(StockTakeItem).filter_by(
                stock_take_id=last_stock_take.stock_take_id
            ).count()
            return {
                "date": last_stock_take.finalize_at.isoformat(),
                "daysAgo": TankStockService.humanize_days_ago(last_stock_take.finalize_at),
                "tankCount": 1,
                "itemCount": item_count,
                "status": last_stock_take.status,
                "remarks": last_stock_take.remarks
            }
        return None
        
    @staticmethod
    def humanize_days_ago(dt):
        delta = (datetime.now() - dt).days

        # Handle special cases
        if delta == 0:
            return "Today"
        elif delta == 1:
            return "Yesterday"
        elif delta < 7:
            return f"{delta} days ago"
        elif delta < 30:
            weeks = delta // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif delta < 365:
            months = delta // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = delta // 365
            return f"{years} year{'s' if years > 1 else ''} ago"

    @staticmethod
    def get_fish_summary(site_id=None, detailed=False):
        total_fish, tank_with_fish_count = TankStockService.get_fish_stats(site_id)
        # active_tank_count = TankStockService.get_active_tank_count(site_id)
        fish_type_count = TankStockService.get_fish_type_count(site_id)

        summary = {
            "totalFishCount": total_fish,
            "tankWithFishCount": tank_with_fish_count,
            "activeTankCount": tank_with_fish_count,
            "fishTypeCount": fish_type_count,
        }

        if detailed:
            summary["tanksWithStock"] = TankStockService.get_tank_utilization(site_id)
            summary["lastStockTake"] = TankStockService.get_last_stock_take(site_id)

        return summary
    
    @staticmethod
    def get_tanks_with_stock(site_id=None):
        query = db.session.query(
            Tank.tank_id,
            db.func.sum(TankStock.quantity).label("total_quantity"),
            Tank.capacity
        ).join(TankStock, Tank.tank_id == TankStock.tank_id)

        if site_id and site_id > 0:
            query = query.filter(Tank.site_id == site_id)

        query = query.filter(TankStock.quantity > 0)

        tank_data = query.group_by(Tank.tank_id, Tank.capacity).all()

        stocked_count = len(tank_data)
        total_tank_count = db.session.query(Tank).filter(
            Tank.site_id == site_id if site_id else True
        ).count()

        total_capacity = sum(tank.capacity or 0 for tank in tank_data)
        total_quantity = sum(tank.total_quantity or 0 for tank in tank_data)

        utilization = (
            (stocked_count / total_tank_count * 100) if total_tank_count > 0 else 0
        )

        capacity_utilization = (
            (total_quantity / total_capacity * 100) if total_capacity > 0 else 0
        )

        return {
            "count": stocked_count,
            "utilizationPercent": round(utilization, 1),
            "capacityUtilizationPercent": round(capacity_utilization, 1)
        }