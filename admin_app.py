# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools
import os
import json

from flask import Flask, request, session, render_template, redirect, g, url_for, abort, jsonify
from models import db, User, Menu, Showcase, Article
from config import Config, DevelopmentConfig
from wtforms import TextField, TextAreaField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import Required, Optional, Length
from datetime import datetime

from flask_wtf import Form
from wtforms import TextField, PasswordField
from wtforms.validators import DataRequired


class LoginForm(Form):
    username = TextField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    otp_token = TextField('两步验证代码', validators=[DataRequired()])

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
        query_factory=Menu.query_all,  # TODO: 如果permission != 'admin'，不显示这一项，显示parent != 'root'的菜单
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name
    )
    title = TextField("标题", validators=[
        Required(),
        Length(max=100)
    ])
    info = TextField("简介（20字以内）", validators=[Required()])
    text = TextAreaField("正文", validators=[Required()])  # TODO: 验证内容合法性 HTML(),sanitize

    def create(self):
        article = Article(**self.data)
        return article.save()


app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)
db.app = app
from flask_debugtoolbar import DebugToolbarExtension
DebugToolbarExtension(app)


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
        return redirect("http://whouz.com")
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


@app.route('/upload/image', methods=['POST'])
@login_required
def upload_file():
    import uuid
    file = request.files['upload_file']
    if file:
        filename = "".join([str(uuid.uuid4()), ".", file.filename.split(".")[-1]])
        file.save(os.path.join(app.root_path, "static", app.config['UPLOAD_FOLDER'], filename))
        return jsonify(
            success=True,
            msg="呵呵",
            file_path=url_for("static", filename="%s/%s" % (app.config["UPLOAD_FOLDER"] ,filename))
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
    list = Menu.query.filter_by(id=uid).first()
    db.session.delete(list)
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
        db.session.add(menu)
        db.session.commit()

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
        menu.parent = request.form['parent']
        db.session.add(menu)
        db.session.commit()
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
        db.session.add(showcase)
        db.session.commit()

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
        db.session.add(slider)
        db.session.commit()
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
            db.session.add(user)
            db.session.commit()
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
            raise ValueError('请输入登录用户名')
        if request.form['nickname'] is None:
            raise ValueError('请输入前端显示用户名')
        if request.form['password'] is None:
            raise ValueError('请输入登录密码')
        if request.form['permission'] is None:
            raise ValueError('请输入权限信息')
        user = User()
        user.name = request.form['username']
        user.nickname = request.form['nickname']
        user.password = request.form['password']
        user.permission = request.form['permission']
        otop = user.regenerate_otp_token()
        db.session.add(user)
        db.session.commit()
        return render_template("admin/qrcode.html", otop=otop)

    if request.method == "GET":
        return render_template('admin/add-user.html')


@app.route("/user/<int:uid>/detail", methods=['GET', 'POST'])
@root_required
def user_detail(uid):
    if request.method == 'GET':
        user = User.query.filter_by(id=uid).first()
        dic = {'username': user.name, 'nickname': user.nickname, 'password': user.password, 'permission': user.permission}
        return json.dumps(dic)

    if request.method == 'POST':
        user = User.query.filter_by(id=uid).first()
        user.name = request.form['username']
        user.nickname = request.form['nickname']
        if request.form['password'] != "":
            user.password = request.form['password']
        user.permission = request.form['permission']
        db.session.add(user)
        db.session.commit()
        return "success"


@app.route("/user/info", methods=['GET', 'POST'])
@login_required
def user_info():
    if request.method == 'GET':
        return render_template("admin/user-info.html", user=g.user)

    if request.method == 'POST':
        user = g.user
        user.name = request.form['username']
        user.nickname = request.form['nickname']
        if request.form['password'] != '':
            user.password = request.form['password']
        db.session.add(user)
        db.session.commit()
        return render_template("admin/user-info.html", user=user)


########################################################################################################################
@app.route("/article")
@login_required
def admin_article_list():
    if g.user.permission != 'admin':
        article = Article.query.filter_by(secondary=g.user.permission, show_flag=True).order_by("-id").all()
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
            ID = int(request.form['secondary'])
            secondary_new = Menu.query.filter_by(id=ID).first()
            article.secondary = secondary_new
            article.date = datetime.now()
            article.info = request.form['info']
            db.session.add(article)
            db.session.commit()
            return redirect("/article")

        return render_template('admin/add-article.html', form=form)
    else:
        return redirect("/article")


@app.route("/article/<int:uid>/del")
@login_required
def article_del(uid):
    article = Article.query.filter_by(id=uid).first()
    if g.user.permission == article.secondary.name or g.user.permission == 'admin':
        article.show_flag = False
        db.session.add(article)
        db.session.commit()
        return "success"
    else:
        return 'No Permission!'


########################################################################################################################


if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000, debug=True)