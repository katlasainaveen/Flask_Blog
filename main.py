from flask import Flask, render_template, redirect, url_for, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_ckeditor import CKEditor
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_login import current_user, login_user, logout_user, login_required, LoginManager, UserMixin
from datetime import date
from werkzeug.security import check_password_hash, generate_password_hash
from flask_gravatar import Gravatar

from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)

# image for commenters
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ckeditor = CKEditor(app)


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = relationship("User", back_populates="posts")

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    comments = relationship("Comment", back_populates="parent_post")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True)
    password = db.Column(db.String(250), nullable=False)

    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


db.create_all()
db.session.commit()


# decorator
def admin_only(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        if current_user.id == 1:
            return function(*args, *kwargs)
        else:
            return abort(403)

    return wrapper_function


@app.route("/")
def home():
    data = db.session.query(BlogPost).all()
    return render_template('index.html', all_posts=data)


@app.route("/about")
def about():
    return render_template('about.html')


@app.route("/contact")
def contact():
    return render_template('contact.html')


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    form = CommentForm()
    data = BlogPost.query.get(post_id)

    if form.validate_on_submit():
        if current_user.is_authenticated:
            data2 = Comment(
                text=form.body.data,
                comment_author=current_user,
                parent_post=data
            )
            db.session.add(data2)
            db.session.commit()

        else:
            return redirect(url_for('login', error="You need to login to add a comment"))

    return render_template('post.html', post=data, form=form)


@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    data = BlogPost.query.get(post_id)
    db.session.delete(data)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/edit/<int:post_id>", methods=["POST", "GET"])
@login_required
@admin_only
def edit_post(post_id):
    data = BlogPost.query.get(post_id)
    form = CreatePostForm(
        title=data.title,
        subtitle=data.subtitle,
        img_url=data.img_url,
        body=data.body,
    )

    if form.validate_on_submit():
        data.title = form.title.data
        data.subtitle = form.subtitle.data
        data.body = form.body.data
        data.img_url = form.img_url.data
        db.session.commit()
        return redirect(url_for('show_post', post_id=data.id))

    return render_template('make-post.html', form=form, is_edit=True)


@app.route("/add", methods=["POST", "GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        data = BlogPost(
            author=current_user,
            title=form.title.data,
            subtitle=form.subtitle.data,
            date=date.today().strftime("%B %d, %Y"),
            body=form.body.data,
            img_url=form.img_url.data,
        )
        db.session.add(data)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('make-post.html', form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/login", methods=["POST", "GET"])
def login():
    error = None
    form = LoginForm()
    if form.validate_on_submit():
        data = User.query.filter_by(email=form.email.data).first()

        if data == None:
            error = "User doesn't Exist"

        else:
            if check_password_hash(data.password, form.password.data):
                login_user(data)
                return redirect(url_for('home'))

            else:
                error = "Incorrect Password"

    return render_template('login.html', form=form, error=error)


@app.route("/register", methods=["POST", "GET"])
def register():
    form = RegisterForm()
    error = None
    if form.validate_on_submit():
        data = User.query.filter_by(email=form.email.data).first()

        if data == None:
            data = User(
                email=form.email.data,
                name=form.name.data,
                password=generate_password_hash(password=form.password.data, method="pbkdf2:sha256", salt_length=8)
            )
            db.session.add(data)
            db.session.commit()

            login_user(data)
            return redirect(url_for('home'))

        else:
            error = "User Exists"

    return render_template('register.html', form=form, error=error)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
