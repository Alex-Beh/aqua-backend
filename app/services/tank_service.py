from app import db
from app.models import Tank, Site
from app.utils import paginate_response
from datetime import datetime

from app.utils.api_response import api_response
class TankService:

    @staticmethod
    def get_paginated(page, size, status=None, site_id=None, sort_field='tank_code', sort_order='asc'):
        query = Tank.query.filter(Tank.deleted_at.is_(None))
        
        if status:
            query = query.filter(Tank.status == status.capitalize())
        
        if site_id:
            query = query.filter(Tank.site_id == site_id)
        
        # Paginate the results
        return paginate_response(query, page, size, Tank, sort_field, sort_order)

    @staticmethod
    def get_all(status=None, site_id=None):
        query = Tank.query.filter(Tank.deleted_at.is_(None))
        
        if status:
            query = query.filter(Tank.status == status.capitalize())
        
        if site_id:
            query = query.filter(Tank.site_id == site_id)
        
        return query.all()

    @staticmethod
    def get_by_id(tank_id):
        return Tank.query.get(tank_id)

    @staticmethod
    def get_by_code(tank_code):
        return Tank.query.filter_by(tank_code=tank_code.upper(), deleted_at=None).first()

    @staticmethod
    def create(data, performed_by=None):
        # Validate
        validation_errors = TankService.validate_fields(data)
        if validation_errors:
            return api_response("Validation errors occurred", errors=validation_errors, status_code=400)

        # Generate tank code
        try:
            tank_code = TankService.generate_auto_code(data['siteId'])
        except ValueError as e:
            return api_response(f"Error generating tank code: {str(e)}", status_code=400)

        # Create the tank
        new_tank = Tank(
            site_id=data['siteId'],
            tank_name=data['tankName'],
            tank_code=tank_code.upper(),
            capacity=data.get('capacity'),
            size=data.get('size', 'medium').lower(),
            status=data.get('status', 'Active').capitalize(),
            health_status=data.get('healthStatus', 'healthy').lower(),
            created_at=db.func.current_timestamp(),
            created_by=performed_by
        )
        db.session.add(new_tank)
        db.session.commit()
        return api_response("Tank created successfully", data=new_tank.to_dict(), status_code=201)


    @staticmethod
    def update(tank_id, data, performed_by=None):
        tank = Tank.query.get(tank_id)
        if not tank or tank.deleted_at:
            return api_response("Tank not found", status_code=404)

        validation_errors = TankService.validate_fields(data, for_update=True)
        if validation_errors:
            return api_response("Validation errors occurred", errors=validation_errors, status_code=400)

        # Update tank fields
        tank.tank_name = data.get('tankName', tank.tank_name)
        tank.capacity = data.get('capacity', tank.capacity)
        tank.status = data.get('status', tank.status).capitalize()
        if 'healthStatus' in data:
            tank.health_status = data['healthStatus'].lower()

        if 'size' in data:
            tank.size = data['size'].lower()
                
        tank.updated_at = db.func.current_timestamp()
        tank.updated_by = performed_by
        db.session.commit()
        return api_response("Tank updated successfully", data=tank.to_dict())

    @staticmethod
    def record_health_check(tank_id, status, performed_by=None):
        tank = Tank.query.get(tank_id)
        if not tank or tank.deleted_at:
            return api_response("Tank not found", status_code=404)

        if not status or status.lower() not in ['healthy', 'unhealthy']:
            return api_response("Invalid health status", status_code=400)

        tank.health_status = status.lower()
        tank.last_health_check_at = db.func.current_timestamp()
        tank.last_health_check_by = performed_by
        tank.updated_at = db.func.current_timestamp()
        tank.updated_by = performed_by
        db.session.commit()
        return api_response("Health check recorded", data=tank.to_dict())

    @staticmethod
    def delete(tank_id, performed_by=None):
        tank = Tank.query.get(tank_id)

        # Check if tank exists and is not already deleted
        if not tank or tank.deleted_at:
            return api_response("Tank not found", status_code=404)

        # Check if tank can be deleted
        if not TankService.can_be_deleted(tank):
            return api_response("Cannot delete: Tank still has fish stock.", status_code=400)

        TankService.soft_delete(tank, performed_by)
        db.session.commit()
        return api_response("Tank deleted successfully")

    @staticmethod
    def batch_create(data, performed_by=None):
        validation_errors = TankService.validate_fields(data, is_batch=True)
        if validation_errors:
            return api_response("Validation errors occurred", errors=validation_errors, status_code=400)

        created_tanks = []
        try:
            count = int(data['count'])
            site_id = data['siteId']
            prefix = data['prefix']
            status = data.get('status', 'Active')
            size = data.get('size', 'medium').lower()
            capacity = data.get('capacity', 50)

            if capacity == 0:  # Adjust capacity if it is set to 0
                capacity = 50

            existing_count = Tank.query.filter_by(site_id=site_id).count()
            if existing_count + count > 999:
                return api_response("Batch exceeds maximum allowed tanks (999) for this site", status_code=400)

            for i in range(1, count + 1):
                tank_code = TankService.generate_auto_code(site_id)
                tank_name = f"{prefix}{str(existing_count + i).zfill(3)}"
                
                new_tank = Tank(
                    tank_name=tank_name,
                    tank_code=tank_code,
                    site_id=site_id,
                    status=status,
                    size=size,
                    capacity=capacity,
                    created_at=db.func.current_timestamp(),
                    created_by=performed_by
                )
                db.session.add(new_tank)
                created_tanks.append(new_tank)

            db.session.commit()
        except (ValueError, TypeError) as e:
            return api_response(f"Error processing batch: {str(e)}", status_code=400)
        
        return api_response(f"{len(created_tanks)} tanks created successfully", data=[tank.to_dict() for tank in created_tanks])

    @staticmethod
    def validate_fields(data, for_update=False, is_batch=False):
        errors = {}

        if not data.get('siteId'):
            errors['siteId'] = "Site ID is required"
        else:
            site = Site.query.filter_by(site_id=data['siteId'], deleted_at=None).first()
            if not site:
                errors['siteId'] = "Invalid or deleted Site ID"

        if is_batch:
            if not data.get('prefix'):
                errors['prefix'] = "Prefix is required"
            if not data.get('count'):
                errors['count'] = "Count is required"
            else:
                try:
                    count = int(data['count'])
                    if count <= 0:
                        errors['count'] = "Count must be a positive number"
                except (ValueError, TypeError):
                    errors['count'] = "Count must be a valid integer"
        else:
            if not data.get('tankName'):
                errors['tankName'] = "Tank Name is required"

            # Only validate status if not batch
            status = data.get('status')
            if not status:
                errors['status'] = "Status is required"
            elif status.lower() not in ['active', 'maintenance', 'retired']:
                errors['status'] = "Invalid status value"

            health_status = data.get('healthStatus')
            if health_status and health_status.lower() not in ['healthy', 'unhealthy']:
                errors['healthStatus'] = "Invalid health status value"

        # Capacity validation (ensure it is a positive integer or zero)
        if 'capacity' in data:
            try:
                capacity = int(data['capacity'])
                if capacity < 0:
                    errors['capacity'] = "Capacity must be a positive number or zero."
            except (ValueError, TypeError):
                errors['capacity'] = "Capacity must be a valid number."
        else:
            data['capacity'] = 50

        # Size validation
        if 'size' in data and data['size'] is not None:
            size = data['size'].lower()
            valid_sizes = ['small', 'medium', 'big']

            if size not in valid_sizes:
                errors['size'] = f"Size must be one of: {', '.join(valid_sizes)}"

        return errors if errors else None

    @staticmethod
    def generate_auto_code(site_id):
        site = Site.query.get(site_id)
        
        if not site:
            raise ValueError("Invalid site ID provided.")
        
        site_code = site.site_code.upper() if site.site_code else 'UNKNOWN'

        # Ensure that no duplicate tank codes exist for this site
        existing_count = Tank.query.filter_by(site_id=site_id).count()
        
        if existing_count > 999:
            raise ValueError("Maximum tank limit reached for this site.")
        
        next_number = existing_count + 1
        return f"T-{site_code}-{str(next_number).zfill(3)}"

    @staticmethod
    def soft_delete(tank, performed_by=None):
        """Marks the record as deleted"""
        tank.deleted_at = db.func.current_timestamp()
        tank.updated_at = db.func.current_timestamp()
        tank.deleted_by = performed_by
        db.session.add(tank)
        return tank

    @staticmethod
    def can_be_deleted(tank):
        """Check if the tank has no stock left (safe to delete)."""
        for stock in tank.stocks:
            if stock.quantity > 0:
                return False
        return True