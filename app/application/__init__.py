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
        from . import routes  # Import routes 
        from . import models # Import models
        # db.drop_all()
        db.create_all()  # Create SQL tables for our data models

        return app