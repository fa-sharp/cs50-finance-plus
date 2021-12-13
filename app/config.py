"""Flask config variables."""
from application import db
from os import environ
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Set Flask configuration from .env file."""

    # General Config
    FLASK_APP = environ.get('FLASK_APP')
    FLASK_ENV = environ.get('FLASK_ENV')
    TEMPLATES_AUTO_RELOAD = True

    # Database
    SQLALCHEMY_DATABASE_URI = environ.get("POSTGRES_URL")
    SQLALCHEMY_ECHO = True if FLASK_ENV == "development" else False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask Session
    SESSION_TYPE = "sqlalchemy"
    SESSION_SQLALCHEMY = db
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 # one day

    # IEX (Stock data) API key https://iextrading.com/developer
    API_KEY = environ.get("API_KEY")