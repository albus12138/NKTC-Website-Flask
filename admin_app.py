#coding: utf-8
from __future__ import unicode_literals

import functools
import os

from flask import Flask, request, session, render_template, redirect, g, url_for, abort, jsonify
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
    secondary = QuerySelectField(
        "要...发到哪里",
        validators=[Required()],
        query_factory=Menu.query_all,  # TODO: 所有parent不为'root'的菜单项，如果permission != 'admin'，不显示这一项
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name
    )
    title = TextField("标题", validators=[
        Required(),
        Length(max=100)
    ])
    text = TextAreaField("正文", validators=[Required()])

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


@app.route("/list-del/<uid>")
@root_required
def del_list(uid):
    list = Menu.query.filter_by(id=uid).first()
    db.session.delete(list)
    db.session.commit()
    return redirect(url_for('admin_list'))


########################################################################################################################
@app.route("/slider")
@root_required
def admin_slider():
    showcase = Showcase.query.order_by("-id").all()
    return render_template('admin/slider.html', showcase=showcase)


@app.route("/slider-del/<uid>")
@root_required
def del_slider(uid):
    slider = Showcase.query.filter_by(id=uid).first()
    db.session.delete(slider)
    db.session.commit()
    return redirect(url_for('admin_slider'))


########################################################################################################################
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
        return render_template('admin/user.html', users=User.query.all())


@app.route("/user/<uid>/del")
@root_required
def del_user(uid):
    user = User.query.filter_by(id=uid).first()
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_user'))


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


########################################################################################################################
@app.route("/article")
@login_required
def admin_article_list():
    article = Article.query.order_by("-id").all()
    return render_template('admin/article-list.html', article=article)


@app.route("/article/add", methods=["GET", "POST"])
@login_required
def add_article():
    form = CreateArticleForm()
    if form.validate_on_submit():
        form.create()
        return redirect("/")
    return render_template("admin/add_article.html", form=form)


@app.route("/article/<int:uid>")
@login_required
def article_edit(uid):
    article = Article.query.filter_by(id=uid).first()
    if g.user.permission == article.secondary or g.user.permission == 'admin':  # TODO:文章分类
        form = None  # TODO: 把对应ID文章填入form，返回到编辑器
        return render_template('admin/add_article.html', form=form)
    else:
        return abort(401)


@app.route("/article/<int:uid>/del")
@login_required
def article_del(uid):
    article = Article.query.filter_by(id=uid).first()
    if g.user.permission == article.secondary or g.user.permission == 'admin':  # TODO:文章分类
        db.session.delete(article)
        db.session.commit()
        return 0
    else:
        return 'No Permission!'


########################################################################################################################
@app.errorhandler(404)
def page_not_found(error):
    return redirect("http://whouz.com")


@app.errorhandler(401)
def no_permission(error):
    return redirect("http://whouz.com")


if __name__ == '__main__':
    app.run(port=5000, debug=True)