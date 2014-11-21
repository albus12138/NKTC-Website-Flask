#-*- coding:utf-8  -*-

from flask import Flask, render_template, flash, request, session, redirect, url_for
from datetime import  datetime

from models import Menu, Article, User, Showcase, db
from config import Config, DevelopmentConfig


#config
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)
db.app = app
from flask_debugtoolbar import DebugToolbarExtension
DebugToolbarExtension(app)

#Function
def get_menu(name):
    menu = Menu.query.filter_by(parent=name).all()
    return menu

#Flask
@app.route('/')
def index():
    menu = get_menu('root')
    showcase = Showcase.query.all()
    news_1 = Article.query.filter_by(main="NKTC").order_by("-date")
    news_2 = Article.query.filter_by(main=u'学生会').order_by("-date")
    news_3 = Article.query.filter_by(main=u'社团活动').order_by("-date")
    return render_template('index.html', menu=menu, showcase=showcase, news_1=news_1, news_2=news_2, news_3=news_3)


@app.route('/category/<name>/<title>')
def list(name, title):
    if title is 'root':
        x = get_menu(name)
        title = x[0]
    main_menu = get_menu('root')
    secondary = Menu.query.filter_by(name=title).first()
    secondary_menu = get_menu(name)
    content = Article.query.filter_by(main=name, secondary=secondary).all()
    for item in content:
        item.date = item.date.strftime("%Y-%m-%d %X")
    return render_template('list.html', menu=main_menu, list=secondary_menu, news=content, title=title, parent=name)


@app.route('/article/<title>')
def page(title):
    menu = get_menu('root')
    content = Article.query.filter_by(title=title).first()
    news = Article.query.filter_by(secondary=content.secondary).all()
    content.date = content.date.strftime("%Y-%m-%d %X")
    return render_template('page.html', menu=menu, content=content, news=news, title=content.secondary.name, parent=content.secondary.parent)


if __name__ == '__main__':
    app.run(port=80, debug=True)