from app import db
from flask_login import UserMixin
from sqlalchemy import CheckConstraint, Index, func


class AppUser(db.Model, UserMixin):
    __tablename__ = 'app_user'

    __table_args__ = (
        Index('ix_app_user_role_id', 'role_id'),
        Index('ix_app_user_status', 'status'),
        # Case-insensitive unique email (Postgres):
        # Index('uq_app_user_email_lower', func.lower(email), unique=True),
        # For portability, keep column unique and enforce lowercase in service layer.
    )

    user_id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.String(50))
    username = db.Column(db.String(50), unique=True, nullable=False)

    name = db.Column(db.String(100))

    # consider nullable=False if required
    email = db.Column(db.String(255), unique=True)
    phone_number = db.Column(db.String(20))

    password_hash = db.Column(db.Text, nullable=False)

    # Consider using Enum('active','inactive','suspended', name='user_status')
    status = db.Column(db.String(20), default='active')

    role_id = db.Column(db.Integer, db.ForeignKey(
        'role.role_id', ondelete='RESTRICT'), index=True)

    joined_date = db.Column(db.Date, server_default=func.current_date())
    resigned_date = db.Column(db.Date)

    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(), nullable=False)
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_onupdate=func.now())
    deleted_by = db.Column(db.String(100))
    deleted_at = db.Column(db.DateTime(timezone=True))

    role = db.relationship("Role", backref="users", lazy="selectin")

    # Flask-Login compatibility
    def get_id(self):  # explicit string return
        return str(self.user_id)

    def __repr__(self):
        return f"<User {self.username}>"

    @property
    def is_active(self):
        return (self.status or '').lower() == 'active'

    @property
    def is_admin(self):
        return bool(self.role and (self.role.role_name or '').lower() == 'admin')

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'staff_id': self.staff_id,
            'username': self.username,
            'name': self.name,
            'email': self.email,
            'phone_number': self.phone_number,
            'status': self.status,
            'role_id': self.role_id,
            'joined_date': self.joined_date.isoformat() if self.joined_date else None,
            'resigned_date': self.resigned_date.isoformat() if self.resigned_date else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_by': self.deleted_by,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
        }

    def to_safe_dict(self):
        return {
            "user_id": self.user_id,
            "staff_id": self.staff_id,
            "username": self.username,
            "name": self.name,
            "role": self.role.role_name if self.role else None,
            "role_id": self.role_id
        }
