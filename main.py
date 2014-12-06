# -*- coding:utf-8  -*-

from flask import Flask, render_template, redirect, url_for, abort

from models import Menu, Article, Showcase, db
from config import DevelopmentConfig
# from config import Config


# config
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)
db.app = app
from flask_debugtoolbar import DebugToolbarExtension
DebugToolbarExtension(app)


# Function
def get_menu(name):
    menu = Menu.query.filter_by(parent=name).all()
    return menu


# Flask
@app.route('/')
def index():
    menu = get_menu('root')
    showcase = Showcase.query.all()
    news_1 = Article.query.filter_by(main="NKTC", show_flag=True).order_by("-date")
    news_2 = Article.query.filter_by(main=u'学生会', show_flag=True).order_by("-date")
    news_3 = Article.query.filter_by(main=u'社团活动', show_flag=True).order_by("-date")
    for item in news_1:
        where = item.text.find('</p>')
        if where > 20:
            where = 20
        item.text = item.text[3:where]
    for item in news_2:
        where = item.text.find('</p>')
        if where > 20:
            where = 20
        item.text = item.text[3:where]
    for item in news_2:
        where = item.text.find('</p>')
        if where > 20:
            where = 20
        item.text = item.text[3:where]
    return render_template('index.html', menu=menu, showcase=showcase, news_1=news_1, news_2=news_2, news_3=news_3)


@app.route('/category/<name>/<title>')
def list(name, title):
    if title == 'root':
        x = get_menu(name)
        title = x[0]
        return redirect(url_for('list', name=name, title=title.name))
    main_menu = get_menu('root')
    secondary = Menu.query.filter_by(name=title).first()
    secondary_menu = get_menu(name)
    content = Article.query.filter_by(main=name, secondary=secondary, show_flag=True).all()
    for item in content:
        item.date = item.date.strftime("%Y-%m-%d %X")
    return render_template('list.html', menu=main_menu, list=secondary_menu, news=content, title=title, parent=name)


@app.route('/article/<title>')
def page(title):
    menu = get_menu('root')
    content = Article.query.filter_by(title=title).first()
    news = Article.query.filter_by(secondary=content.secondary, show_flag=True).all()
    if content.show_flag is True:
        content.date = content.date.strftime("%Y-%m-%d %X")
        content.click()
        return render_template('page.html', menu=menu, content=content, news=news, title=content.secondary.name, parent=content.secondary.parent)
    else:
        return abort(404)


if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5050, debug=True)