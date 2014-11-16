import os
BASEDIR = os.path.dirname(os.path.abspath(__file__))

class Config(object):
    DEGUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///NKTC.db'
    SECRET_KEY = '233'
    UPLOAD_FOLDER = os.path.join(BASEDIR, "static/upload")


class DevelopmentConfig(Config):
    DEGUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///Development.db'
    SECRET_KEY = '233'
