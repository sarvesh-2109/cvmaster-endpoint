from flask import Flask
from config import Config
from app.extensions import db, migrate, jwt
from app.routes.auth import auth_bp
from app.routes.resume import resume_bp
from app.routes.roast import roast_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(roast_bp)

    return app
