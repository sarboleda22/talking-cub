"""Configuration file containing the different configuration for our app,
depending on what environment it is run"""
import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))
MAX_INQUIRIES = 10

class Config:
    """Base configuration"""
    DEBUG = False

class Dev(Config):
    """Configuration to be used in Dev environments"""
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:mysecretpassword@localhost:5432/talking_cub"
    SECRET_KEY = 'S@MpLe9SeCrEt#KeY'
    DEBUG = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class Prod(Config):
    """Configuration to be used in production"""
    SQLALCHEMY_DATABASE_URI = 'sqlite://:memory:' #TODO os.environ['DATABASE_URL']

class Test(Dev):
    """Configuration to be used in testing environments"""
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    TESTING = True
