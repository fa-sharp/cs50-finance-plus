from flask import Flask
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_app():
    """Construct the core application."""
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')

    db.init_app(app) # Initialize SQL Alchemy
    Session(app) # Initialize Flask-Session

    with app.app_context():
        from . import create_routes  # Import routes 
        from . import models # Import models
        from .jinja_filters import cash_flow, commas, percent, usd # Import and apply Jinja filters
        for filter in [cash_flow, commas, percent, usd]:
            app.jinja_env.filters[filter.__name__] = filter
        
        ####### db.drop_all() # Drop DB tables (if needed)
        ####### db.create_all()  # Create DB tables based on models.py (if needed)

        return app