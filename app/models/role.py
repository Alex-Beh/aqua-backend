from app import db

class Role(db.Model):
    __tablename__ = 'role'
    
    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)

    # Optional: relationship to AppUser
    users = db.relationship('AppUser', backref='role', lazy=True)

    def __repr__(self):
        return f"<Role {self.name}>"
    
    def to_dict(self):
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "description": self.description
        }