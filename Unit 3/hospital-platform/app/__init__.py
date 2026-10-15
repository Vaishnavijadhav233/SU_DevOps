import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///hospital.db"),
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from app.routes import api_bp
    from app.metrics import register_metrics
    app.register_blueprint(api_bp, url_prefix="/api")
    register_metrics(app)

    with app.app_context():
        db.create_all()
        from app.services import seed_data
        seed_data()
    return app
