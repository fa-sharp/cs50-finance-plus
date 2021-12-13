"""Flask config variables."""
from application import db
from os import environ, path
from dotenv import load_dotenv
from tempfile import mkdtemp

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))


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