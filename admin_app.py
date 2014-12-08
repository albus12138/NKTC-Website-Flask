# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools
import os
import json

from flask import Flask, request, session, render_template, redirect, g, url_for, abort, jsonify, flash
from models import db, User, Menu, Showcase, Article
from wtforms import TextField, TextAreaField, PasswordField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import Required, Length, DataRequired
from datetime import datetime
from sanitize import HTML
from flask_wtf import Form

from config import DevelopmentConfig
# from config import Config


class LoginForm(Form):
    username = TextField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    otp_token = TextField('动态验证码', validators=[DataRequired()])

    def validate_password(self, field):
        account = self.username.data
        user = User.query.filter_by(name=account).first()
        if user and user.locked:
            raise ValueError("账户已锁定，请联系管理员")

        if user and user.check_password(field.data):
            self.user = user
            return user
        else:
            user.failed_times += 1
            if user.failed_times >= 5:
                user.locked = True
            user.save()
        raise ValueError("用户名或密码错误")

    def validate_otp_token(self, field):
        account = self.username.data
        user = User.query.filter_by(name=account).first()
        if user and user.validate_otp(self.otp_token.data):
            return user
        raise ValueError("两部验证代码错误")

    def login(self):
        self.user.failed_times = 0
        self.user.save()
        session["id"] = self.user.id
        self.user.login_time = datetime.now()


class CreateArticleForm(Form):
    secondary = QuerySelectField(
        "文章所属分类",
        validators=[Required()],
        query_factory=Menu.query_all,
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name
    )
    title = TextField("标题", validators=[
        Required(),
        Length(max=100)
    ])
    info = TextField("简介（20字以内）", validators=[Required()])
    text = TextAreaField("正文", validators=[Required()])

    def create(self):
#        self.text.data = HTML(self.text.data) TODO:安全性与中文不兼容
        article = Article(**self.data)
        return article.save()


app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)
db.app = app


@app.before_request
def load_user():
    if "id" in session:
        user = User.query.filter_by(id=session["id"]).first()
        if user:
            g.user = user


def login_required(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        if not hasattr(g, "user"):
            url = url_for("login")
            if "?" not in url:
                url += "?next=" + request.url
            return redirect(url)
        return method(*args, **kwargs)
    return wrapper


def root_required(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        if not hasattr(g, "user"):
            url = url_for("login")
            if "?" not in url:
                url += "?next=" + request.url
            return redirect(url)
        else:
            user = g.user
            if user.id == 1 or user.permission == 'admin':
                return method(*args, **kwargs)
        return abort(403)
    return wrapper


@app.route("/")
@login_required
def index():
    return redirect(url_for('admin_article_list'))


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        form.login()
        return redirect("/")
    return render_template("admin/login.html", form=form)


@app.route("/logout")
def logout():
    session.pop("id", None)
    return redirect("/login")


@app.route('/upload/image', methods=['POST'])
@login_required
def upload_file():
    import uuid
    f = request.files['upload_file']
    if f:
        filename = "".join([str(uuid.uuid4()), ".", f.filename.split(".")[-1]])
        f.save(os.path.join(app.root_path, "static", app.config['UPLOAD_FOLDER'], filename))
        return jsonify(
            success=True,
            msg="呵呵",
            file_path=url_for("static", filename="%s/%s" % (app.config["UPLOAD_FOLDER"], filename))
        )


########################################################################################################################
@app.route("/list")
@root_required
def admin_list():
    main_menu = Menu.query.filter_by(parent='root').all()
    secondary_menu = {}
    for item in main_menu:
        secondary_menu[item.id] = Menu.query.filter_by(parent=item.name).all()
    return render_template('admin/list.html', main_menu=main_menu, secondary_menu=secondary_menu)


@app.route("/menu/<int:uid>/del")
@root_required
def del_list(uid):
    menu = Menu.query.filter_by(id=uid).first()
    db.session.delete(menu)
    db.session.commit()
    return "success"


@app.route("/menu/add", methods=['GET', 'POST'])
@root_required
def add_menu():
    if request.method == 'GET':
        menu = Menu.query.filter_by(parent='root').all()
        return render_template("admin/add-menu.html", main_menu=menu)

    if request.method == 'POST':
        name = request.form['name']
        parent_id = int(request.form['secondary'])
        if parent_id != 0:
            parent = Menu.query.filter_by(id=parent_id).first()
            parent = parent.name
        else:
            parent = 'root'
        menu = Menu(name, parent)
        menu.save()

        main_menu = Menu.query.filter_by(parent='root').all()
        secondary_menu = {}
        for item in main_menu:
            secondary_menu[item.id] = Menu.query.filter_by(parent=item.name).all()
        return render_template('admin/list.html', main_menu=main_menu, secondary_menu=secondary_menu)


@app.route("/menu/<int:uid>/detail", methods=['GET', 'POST'])
@root_required
def menu_detail(uid):
    if request.method == 'GET':
        menu = Menu.query.filter_by(id=uid).first()
        dic = {'name': menu.name, 'parent': menu.parent}
        return json.dumps(dic)

    if request.method == 'POST':
        menu = Menu.query.filter_by(id=uid).first()
        menu.name = request.form['name']
        parent_id = int(request.form['secondary'])
        if parent_id != 0:
            parent = Menu.query.filter_by(id=parent_id).first()
            menu.parent = parent.name
        else:
            menu.parent = 'root'
        menu.save()
        return "success"


########################################################################################################################
@app.route("/slider")
@root_required
def admin_slider():
    showcase = Showcase.query.order_by("-id").all()
    return render_template('admin/slider.html', showcase=showcase)


@app.route("/slider/<int:uid>/del")
@root_required
def del_slider(uid):
    slider = Showcase.query.filter_by(id=uid).first()
    db.session.delete(slider)
    db.session.commit()
    return "success"


@app.route("/slider/add", methods=["GET", "POST"])
@root_required
def add_slider():
    if request.method == 'GET':
        return render_template("admin/add-slider.html")

    if request.method == 'POST':
        text = request.form['text']
        img = request.form['img']
        url = request.form['url']
        showcase = Showcase()
        showcase.img = img
        showcase.text = text
        showcase.url = url
        showcase.save()

        showcase = Showcase.query.order_by("-id").all()
        return render_template("admin/slider.html", showcase=showcase)


@app.route("/slider/<uid>/detail", methods=['GET', 'POST'])
@root_required
def slider_detail(uid):
    if request.method == 'GET':
        slider = Showcase.query.filter_by(id=uid).first()
        dic = {'text': slider.text, 'img': slider.img, 'url': slider.url}
        return json.dumps(dic)

    if request.method == 'POST':
        slider = Showcase.query.filter_by(id=uid).first()
        slider.text = request.form['text']
        slider.img = request.form['img']
        slider.url = request.form['url']
        slider.save()
        return "success"


########################################################################################################################
@app.route("/user", methods=["GET", "POST"])
@login_required
def admin_user():
    if g.user.permission == 'admin':
        if request.method == "POST":
            user = User.query.filter_by(id=request.form['uid']).first()
            if user.name != request.form['username']:
                user.name = request.form['username']
            if user.nickname != request.form['nickname']:
                user.nickname = request.form['nickname']
            if request.form['password'] != '':
                user.password = request.form['password']
            if user.permission != request.form['permission']:
                user.permission = request.form['permission']
            user.save()
            return redirect(url_for('admin_user'))

        if request.method == "GET":
            users = User.query.all()
            for user in users:
                user.login_time = user.login_time.strftime("%Y-%m-%d %X")
            return render_template('admin/user.html', users=users)
    else:
        return redirect("/user/info")


@app.route("/user/<int:uid>/del")
@root_required
def del_user(uid):
    user = User.query.filter_by(id=uid).first()
    db.session.delete(user)
    db.session.commit()
    return "success"


@app.route("/user/add", methods=["GET", "POST"])
@root_required
def add_user():
    if request.method == "POST":
        if request.form['username'] is None:
            return "fail"
        if request.form['nickname'] is None:
            return "fail"
        if request.form['password'] is None:
            return "fail"
        if request.form['permission'] is None:
            return "fail"
        user = User()
        user.name = request.form['username']
        user.nickname = request.form['nickname']
        user.password = request.form['password']
        user.permission = request.form['permission']
        otop = user.regenerate_otp_token()
        user.save()
        return otop
#        return render_template("admin/qrcode.html", otop=otop)

    if request.method == "GET":
        return render_template('admin/add-user.html')


@app.route("/user/<int:uid>/detail", methods=['GET', 'POST'])
@root_required
def user_detail(uid):
    if request.method == 'GET':
        user = User.query.filter_by(id=uid).first()
        dic = {
            'username': user.name,
            'nickname': user.nickname,
            'password': user.password,
            'permission': user.permission
        }
        return json.dumps(dic)

    if request.method == 'POST':
        user = User.query.filter_by(id=uid).first()
        user.name = request.form['username']
        user.nickname = request.form['nickname']
        if request.form['password'] != "":
            user.password = request.form['password']
        user.permission = request.form['permission']
        user.save()
        return "success"


@app.route("/user/info", methods=['GET', 'POST'])
@login_required
def user_info():
    if request.method == 'GET':
        return render_template("admin/user-info.html", user=g.user)

    if request.method == 'POST':
        user = User.query.filter_by(id=g.user.id).first()
        user.name = request.form['username']
        user.nickname = request.form['nickname']
        if request.form['password'] != '':
            user.password = request.form['password']
        session.pop("id", None)
        user.save()
        return redirect("/login")


########################################################################################################################
@app.route("/article")
@login_required
def admin_article_list():
    if g.user.permission != 'admin':
        secondary = Menu.query.filter_by(name=g.user.permission).first()
        article = Article.query.filter_by(secondary=secondary, show_flag=True).order_by("-id").all()
        for item in article:
            item.date = item.date.strftime("%Y-%m-%d %X")
        return render_template('admin/article-list.html', article=article)
    if g.user.permission == 'admin':
        article = Article.query.filter_by(show_flag=True).order_by("-id").all()
        for item in article:
            item.date = item.date.strftime("%Y-%m-%d %X")
        return render_template('admin/article-list.html', article=article)


@app.route("/article/add", methods=["GET", "POST"])
@login_required
def add_article():
    form = CreateArticleForm()
    if form.validate_on_submit():
        form.create()
        return redirect("/")
    return render_template("admin/add-article.html", form=form)


@app.route("/article/<int:uid>", methods=['GET', 'POST'])
@login_required
def article_edit(uid):
    article = Article.query.filter_by(id=uid).first()
    if g.user.permission == article.secondary.name or g.user.permission == 'admin':
        form = CreateArticleForm()
        form.secondary.data = article.secondary
        form.title.data = article.title
        form.text.data = article.text
        form.info.data = article.info

        if form.validate_on_submit():
            article.title = request.form['title']
            article.text = request.form['text']
            number = int(request.form['secondary'])
            secondary_new = Menu.query.filter_by(id=number).first()
            article.secondary = secondary_new
            article.date = datetime.now()
            article.info = request.form['info']
            article.save()
            return redirect("/article")

        return render_template('admin/add-article.html', form=form)
    else:
        return abort(403)


@app.route("/article/<int:uid>/del")
@login_required
def article_del(uid):
    article = Article.query.filter_by(id=uid).first()
    if g.user.permission == article.secondary.name or g.user.permission == 'admin':
        article.show_flag = False
        article.save()
        return "success"
    else:
        return abort(403)


########################################################################################################################


if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000, debug=True)