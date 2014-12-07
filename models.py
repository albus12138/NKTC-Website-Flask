# coding: utf-8

from flask import g
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


def _get_author_id():
    return g.user and g.user.id


class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)
    parent = db.Column(db.String(20), nullable=False)

    def __init__(self, name, parent):
        self.name = name
        self.parent = parent

    @classmethod
    def query_all(cls):
        from flask import g
        user = g.user
        menus = []
        for menu in cls.query.order_by(Menu.name.asc()).all():
            if user.is_admin or menu.name == user.permission:
                if menu.parent != 'root':
                    menus.append(menu)
        return menus

    def save(self):
        if self.name != '':
            db.session.add(self)
            db.session.commit()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)
    nickname = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(), nullable=False, unique=True)
    otp_token = db.Column(db.String())
    permission = db.Column(db.String(20), nullable=False)
    locked = db.Column(db.Boolean, default=False)
    failed_times = db.Column(db.Integer, default=0)
    login_time = db.Column(db.DateTime(), default=datetime.now())

    @property
    def otp_auth(self):
        from otpauth import OtpAuth
        return OtpAuth(self.otp_token)

    @property
    def is_admin(self):
        return self.id == 1 or self.permission == 'admin'

    def save(self):
        if self.name != '' and self.nickname != '' and self.password != '' and self.permission != '':
            db.session.add(self)
            db.session.commit()

    def regenerate_otp_token(self):
        from werkzeug import security
        self.otp_token = security.gen_salt(16)
        self.save()
        return self.otp_auth.to_uri('totp', self.name, 'MKTC')

    def validate_otp(self, token):
        return True
        #return self.otp_auth.valid_totp(int(token))  # TODO: zly 要带手机

    def check_password(self, p):
        return p == self.password


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20), nullable=False, unique=True)
    text = db.Column(db.Text, nullable=False, unique=True)
    author_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'), index=True, nullable=False,
        default=_get_author_id
    )
    author = db.relationship("User")
    date = db.Column(db.DateTime(), default=datetime.now())
    main = db.Column(db.String(20))
    secondary_id = db.Column(
        db.Integer,
        db.ForeignKey('menu.id'), index=True, nullable=False,
    )
    secondary = db.relationship("Menu")
    ans_click = db.Column(db.Integer)
    show_flag = db.Column(db.Boolean)
    info = db.Column(db.String(20), nullable=False)

    def save(self):
        if self.text != '' and self.title != '' and self.info != '':
            self.ans_click = 0
            self.show_flag = True
            if len(self.info) > 20:
                self.info = self.info[0:21]
            db.session.add(self)
            db.session.commit()

    def click(self):
        self.ans_click += 1

    def __init__(self, title, text, info, secondary):
        self.title = title
        self.text = text
        self.secondary = secondary
        self.main = secondary.parent
        self.info = info


class Showcase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(20), nullable=False, unique=True)
    img = db.Column(db.String(50), nullable=False, unique=True)
    url = db.Column(db.String(50), nullable=False)

    def save(self):
        if self.text != '' and self.img != '' and self.url != '':
            db.session.add(self)
            db.session.commit()