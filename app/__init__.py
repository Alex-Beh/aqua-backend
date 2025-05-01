from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from dotenv import load_dotenv

from app.utils.api_response import api_response

db = SQLAlchemy()
migrate = Migrate()  # Initialize here first
login_manager = LoginManager()

def create_app():
      # Load environment variables from .env file
    load_dotenv()

    app = Flask(__name__)
    # app.config.from_object("app.config.Config")

    # Now use the environment variables
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER')
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 5242880))  # default to 5MB if not set
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

    db.init_app(app)
    migrate.init_app(app, db)  # Migrate must be initialized AFTER db.init_app
    login_manager.init_app(app)
    
    CORS(app)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from app.models.app_user import AppUser

    @login_manager.user_loader
    def load_user(user_id):
        return AppUser.query.get(int(user_id))

    # Custom handler for unauthenticated requests
    @login_manager.unauthorized_handler
    def unauthorized():
        return api_response(
            message="You need to log in to access this resource",
            success=False,
            status_code=401
        )
    
    from app.routes import company_routes, site_routes, fish_type_routes, tank_routes
    app.register_blueprint(company_routes.bp)
    app.register_blueprint(site_routes.bp)
    app.register_blueprint(fish_type_routes.bp)
    app.register_blueprint(fish_type_routes.static_bs)
    app.register_blueprint(tank_routes.tanks_bp)

    from app.routes import adjustments_routes, tank_stock_routes
    app.register_blueprint(adjustments_routes.adjust_bp)
    app.register_blueprint(tank_stock_routes.stock_bp)

    from app.routes import auth_routes, route_routes
    app.register_blueprint(route_routes.role_bp)
    app.register_blueprint(auth_routes.auth_bp)

    return app
