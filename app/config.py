"""Flask config variables."""
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

    # Flask Session
    SESSION_FILE_DIR = mkdtemp()
    SESSION_PERMANENT = False
    SESSION_TYPE = "filesystem"

    # Database
    SQLALCHEMY_DATABASE_URI = environ.get("POSTGRES_URL")
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Stock data API key
    API_KEY = environ.get("API_KEY")