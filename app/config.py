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
    if SQLALCHEMY_DATABASE_URI is None or not SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
        raise RuntimeError("POSTGRES_URL environment variable not properly set! Make sure it's set to your Postgres DB URL and starts with 'postgresql://'")
    
    # Flask Session
    SESSION_TYPE = "sqlalchemy"
    SESSION_SQLALCHEMY = db
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 # one day

    # Finnhub.io (Stock data) API key https://finnhub.io
    API_KEY = environ.get("API_KEY")
    if API_KEY is None:
        raise RuntimeError("API_KEY environment variable not set: Make sure to set up your API key from Finnhub!")