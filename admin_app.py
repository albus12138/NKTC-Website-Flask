#coding: utf-8
from __future__ import unicode_literals

import functools
import os

from flask import Flask, request, session, render_template, redirect, g, url_for, abort
from models import db, User, Menu, Showcase, Article
from config import Config, DevelopmentConfig
from wtforms import TextField, TextAreaField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import Required, Optional, Length

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


class CreateArticleForm(Form):
    secondary = (
        "要...发到哪里",
        validators=[Required()],
        query_factory=Menu.query_all, # TODO: 所有parent不为'root'的菜单项，如果permission != 'admin'，不显示这一项
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name
    )
    title = TextField("标题", validators=[
        Required(),
        Length(max=100)
    ])
    text = TextAreaField("正文", validators=[Required()])

    def create(self, title, text, secondary):
        article = Article(title, text, secondary)
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
        return redirect("http://whouz.com")
    return wrapper


@app.route("/")
@login_required
def index():
    return render_template('index.html')

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
    file = request.files['file']
    if file:
        filename = file.filename  # TODO: unsafe
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return url_for("static", fiename="upload/%s" % filename)


@app.route("/list")
@root_required
def admin_list():
    main_menu = Menu.query.filter_by(parent='root').all()
    secondary_menu = {}
    for item in main_menu:
       secondary_menu[item.name] = Menu.query.filter_by(parent=item.name).all()
    return render_template('admin/list.html', main_menu=main_menu, secondary_menu=secondary_menu)


@app.route("/slider")
@root_required
def admin_slider():
    showcase = Showcase.query.order_by("-id").limit(5)
    return render_template('admin/slider.html', showcase=showcase)

@app.route("/user", methods=["GET", "POST"])
@root_required
def admin_user():
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
        user = User.query.all()
        return render_template('admin/user.html', user=user)


@app.route("/user-del/<uid>")
@root_required
def del_user(uid):
    user = User.query.filter_by(id=uid).first()
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_user'))



@app.route("/article")
@login_required
def admin_article_list(main, second):
    article = Article.query.ilter_by(secondary=g.user.permission).order_by("-id").all()
    return render_template('admin/article-list.html', article=article)


@app.route("/article/add")
@login_required
def add_article():
    form = CreateArticleForm()
    if form.validate_on_submit():
        form.create()
        return redirect("/")
    return render_template("admin/add_article.html", form=form)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404


@app.errorhandler(401)
def no_permission(error):
    return render_template('no_permission.html'), 401


if __name__ == '__main__':
    app.run(port=80, debug=True)