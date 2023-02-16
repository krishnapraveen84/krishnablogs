import smtplib
import datetime
import calendar

from flask import Flask, render_template, request, redirect, url_for, flash, abort
from functools import wraps
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from flask_ckeditor import CKEditor, CKEditorField

# >>>>> creating sqlite database by sqlalchemy ORM(object relational mapper) >>>>>
from sqlalchemy import Integer, String, Column, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from flask_login import login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
import os


sec_key = os.environ.get('SEC_KEY')

app = Flask(__name__)
app.config['SECRET_KEY'] = sec_key

Bootstrap(app)
login_manager = LoginManager(app)
ckeditor = CKEditor(app=app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)
# >>>> Datetime >>>>
date = datetime.date.today()
year = date.year
post_date = f"{calendar.month_name[date.month]} {date.day},{year}"


# >>>> Now we are creating WTF_FORMS <<<<<
class Blog(FlaskForm):
    title = StringField('Blog Post Title', validators=[DataRequired()])
    subtitle = StringField('Subtitle', validators=[DataRequired()])
    # author = StringField('Your Name', validators=[DataRequired()])
    img_url = StringField('Blog Image URl', validators=[DataRequired()])
    body = CKEditorField('Blog Content', validators=[DataRequired()])
    submit = SubmitField('Submit Post')


class Register(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email_id = StringField('Email', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField('Sing UP')


class LogIn(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField("Log In")


class CommentForm(FlaskForm):
    comment = CKEditorField('Comment')
    submit = SubmitField("POST")


engine = create_engine('sqlite:///posts.db', echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)


# <<< we have to create class Posts >>>

# child
class Posts(Base):
    __tablename__ = 'blog_post'
    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False)
    date = Column(String(10))
    body = Column(String, nullable=False)
    img_url = Column(String, nullable=False)
    subtitle = Column(String(250), nullable=False)
    # we have to create a foreign key to link posts and users (primary_key is users_data.id)
    author_id = Column(Integer, ForeignKey('User_data.id'))
    # the user.id will be user primary_key i.e id in the table
    comments = relationship('Comment', backref='post_comment')


# parent
class Users(Base):
    __tablename__ = "User_data"
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    password = Column(String(250), nullable=False)
    # Now one User have many Posts
    posts = relationship('Posts', backref='author')
    # user commented many posts
    comments = relationship('Comment', backref='author_comment')

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


# >>> Now we have to link the comment table
class Comment(Base):
    __tablename__ = 'Comments'
    id = Column(Integer, primary_key=True)
    comment = Column(String, nullable=True)
    # its link with user i.e user_comment to posts
    user_id = Column(Integer, ForeignKey('User_data.id'))
    # its link wit blog_post
    comment_id = Column(Integer, ForeignKey('blog_post.id'))


# Users.blog_post = relationship("Posts", order_by=Posts.id, back_populates='blog_post')
# Base.metadata.create_all(engine)


@login_manager.user_loader
def load_user(user_id):
    return Session().query(Users).get(user_id)


# <<< By this line the table created in the database >>>>
# Base.metadata.create_all(engine)

# >>>> Python Decorators >>>>
def admin_only(function):
    @wraps(function)
    def admin(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return function(*args, **kwargs)

    return admin


@app.route("/")
def one():
    # blog = requests.get(url="https://api.npoint.io/c790b4d5cab58020d391").json()
    session = Session()
    posts = session.query(Posts).all()
    return render_template("index.html", blog=posts, year=year)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = Register()
    if form.validate_on_submit():
        name = request.form.get('name')
        email = request.form.get('email_id')
        password = request.form.get('password')
        print(f"{name} {email} {password}")
        if Session().query(Users).filter_by(email=email).first():
            flash("You already signed up with that email! instead login..")
            return redirect('login')
        has_password = generate_password_hash(method="pbkdf2:sha256", password=password, salt_length=8)
        new_user = Users(name=name, email=email, password=has_password)
        session = Session()
        session.add(new_user)
        session.commit()
        return redirect(url_for('one'))
    return render_template("register.html", form=form, year=year)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LogIn()
    if form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        session = Session()
        log_user = session.query(Users).filter_by(email=email).first()
        if not log_user:
            flash("The Email Does Not Exits! Try Again..")
            return redirect('login')
        elif not check_password_hash(str(log_user.password), password=password):
            flash("Incorrect Password! Try Again..")
            return redirect('login')
        else:
            login_user(user=log_user)
            return redirect(url_for('one'))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('one'))


@app.route("/<name>")
def pages(name):
    return render_template(f"{name}.html", year=year)


@app.route("/blogs/<int:num>", methods=['GET', 'POST'])
def blogs(num):
    form = CommentForm()
    ssion = Session()
    posts = ssion.query(Posts).get(num)
    comment = request.form.get('comment')
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need login or register to post a comment")
            return redirect(url_for('login'))

        author = current_user.id
        session = Session()
        new_comment = Comment(comment=comment, user_id=author, comment_id=num)
        session.add(new_comment)
        session.commit()

    # blog = requests.get(url="https://api.npoint.io/c790b4d5cab58020d391").json()
    return render_template("post.html", blog=posts, form=form, year=year)


@app.route("/contact", methods=['POST'])
def receive_data():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']
        my_email = "krishnapraveentumpala2001@gmail.com"
        password = "vciwphrgtthpxtht"
        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()  # secures the connections so impossible to read our data along the line
            connection.login(user=my_email, password=password)
            connection.sendmail(from_addr=my_email, to_addrs=email,
                                msg=f"\n\nContact_Me\n\n Name: {name}\n\n Email: {email}\n\n Phone: {phone}\n\n Message: {message}")
        print(name)
        print(email)
        print(phone)
        print(message)
        return render_template("contact.html", mesg_sent=True)
    return render_template("contact.html", mesg_sent=False, year=year)


# >>>> Creating new post and add it to our database <<<<<


@app.route('/new_post', methods=['GET', 'POST'])
@login_required
@admin_only
def make_post():
    form = Blog()
    if form.validate_on_submit():
        author = current_user.id
        title = request.form.get('title')
        subtitle = request.form.get('subtitle')
        img_url = request.form.get('img_url')
        body = request.form.get('body')
        date_post = post_date
        c1 = Posts(title=title, date=date_post, author_id=author, body=body, img_url=img_url, subtitle=subtitle)
        session = Session()
        session.add(c1)
        session.commit()
        return redirect(url_for('one'))
    return render_template('make-post.html', form=form, year=year)


@app.route('/edit_post/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_only
def edit_post(id):
    id = id - 1
    session = Session()
    post = session.query(Posts).all()

    form = Blog(title=post[id].title, subtitle=post[id].subtitle, author=post[id].author, img_url=post[id].img_url,
                body=post[id].body)
    if form.validate_on_submit():
        session = Session()
        post = session.query(Posts).all()
        title = request.form.get('title')
        subtitle = request.form.get('subtitle')
        author = request.form.get('author')
        img_url = request.form.get('img_url')
        body = request.form.get('body')
        # date_post = post_date
        post_update = post[id]
        post_update.title = title
        post_update.author = author
        post_update.subtitle = subtitle
        post_update.img_url = img_url
        post_update.body = body
        session.commit()
        return redirect(url_for('one'))

    return render_template('make-post.html', form=form, year=year)


@app.route('/delete/<int:id>', methods=['GET', 'DELETE'])
@login_required
@admin_only
def delete_post(id):
    session = Session()
    post = session.query(Posts).get(id)
    session.delete(post)
    session.commit()
    return redirect(url_for('one'))


app.run(debug=True)
