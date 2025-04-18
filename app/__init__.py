from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()  # Initialize here first

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    db.init_app(app)
    migrate.init_app(app, db)  # Migrate must be initialized AFTER db.init_app

    CORS(app)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from app.routes import company_routes, site_routes, fish_type_routes, tank_routes
    app.register_blueprint(company_routes.bp)
    app.register_blueprint(site_routes.bp)
    app.register_blueprint(fish_type_routes.bp)
    app.register_blueprint(fish_type_routes.static_bs)
    app.register_blueprint(tank_routes.bp)

    return app
