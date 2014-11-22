class Config(object):
    DEGUG = False
    SQLALCHEMY_DATABASE_URI = 'mysql://python:rmxypmddSOQv0ny8bAjhbe7pobfJRISY@rdsamizfjqznbmu.mysql.rds.aliyuncs.com/python_nktry'
    SECRET_KEY = "\x7f\xb9\x82\xceY\x8d\x19\x85\xc0\x14\xc8\xb9\x9a??\xa5\xd3\xccew\xa8\x91\xb0;"
    UPLOAD_FOLDER = "upload"


class DevelopmentConfig(Config):
    DEGUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///Development.db'
    SECRET_KEY = "\x7f\xb9\x82\xceY\x8d\x19\x85\xc0\x14\xc8\xb9\x9a??\xa5\xd3\xccew\xa8\x91\xb0;"
    DEBUG_TB_ENABLED = True
