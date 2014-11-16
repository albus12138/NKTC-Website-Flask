#coding: utf-8
from __future__ import unicode_literals

from main import app
from models import db, User, Menu, Article, Showcase
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

manager = Manager(app)

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

@manager.command
def create_all():
    db.create_all()


@manager.command
def add_user():
    with app.app_context():
        username = raw_input("Username: ")
        nickname = raw_input("Nickname: ")
        password = raw_input("Password: ")
        user = User()
        user.name = username
        user.nickname = nickname
        user.password = password
        str = user.regenerate_otp_token()
        print str


if __name__ == '__main__':
    manager.run()
