from app import db
from flask_login import UserMixin

from app.models.role import Role

class AppUser(db.Model, UserMixin):
    __tablename__ = 'app_user'

    user_id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.String(50))
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100))
    emailid = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    password_hash = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20))
    
    role_id = db.Column(db.Integer, db.ForeignKey('role.role_id'))

    joined_date = db.Column(db.Date, default=db.func.current_date())
    resigned_date = db.Column(db.Date)

    created_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_by = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    deleted_by = db.Column(db.Integer)
    deleted_at = db.Column(db.DateTime)

    # Flask-Login compatibility
    @property
    def id(self):
        return self.user_id
    
    def __repr__(self):
        return f"<User {self.username}>"
    
    @property
    def is_active(self):
        return self.status.lower() == 'active'
    
    
    def to_dict(self):
        """
        Convert the AppUser object to a dictionary representation.
        This is useful for returning JSON data in Flask responses.
        """
        return {
            'user_id': self.user_id,
            'staff_id': self.staff_id,
            'username': self.username,
            'name': self.name,
            'emailid': self.emailid,
            'phone_number': self.phone_number,
            'status': self.status,
            'role_id': self.role_id,
            'joined_date': self.joined_date,
            'resigned_date': self.resigned_date,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at,
            'deleted_by': self.deleted_by,
            'deleted_at': self.deleted_at,
        }