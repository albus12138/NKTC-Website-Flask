class Config(object):
    DEGUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///NKTC.db'
    SECRET_KEY = '233'
    UPLOAD_FOLDER = "upload"


class DevelopmentConfig(Config):
    DEGUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///Development.db'
    SECRET_KEY = '233'
    DEBUG_TB_ENABLED = True
