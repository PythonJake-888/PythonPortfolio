import os
from datetime import datetime
from flask import session

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

import cloudinary
import cloudinary.uploader

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    UserMixin,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash

# (local dev only) loads .env if present; harmless on Render
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


app = Flask(__name__)

# ==========================
# CONFIG
# ==========================
app.secret_key = os.getenv("SECRET_KEY", "dev-change-me")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Render Postgres should supply DATABASE_URL
database_url = os.getenv("DATABASE_URL")

# Local fallback
if not database_url:
    database_url = "sqlite:///" + os.path.join(BASE_DIR, "portfolio.db")

# Render sometimes uses postgres:// which SQLAlchemy wants as postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

# ==========================
# AUTH (LOGIN)
# ==========================
login_manager = LoginManager(app)
login_manager.login_view = "login"


# ==========================
# MODELS
# ==========================

from flask_login import UserMixin

class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(300))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    tech = db.Column(db.String(200))
    github = db.Column(db.String(300))
    demo_url = db.Column(db.String(300))
    has_demo = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    media = db.relationship(
        "ProjectMedia",
        backref="project",
        lazy=True,
        cascade="all,delete-orphan",
        order_by="ProjectMedia.created_at.asc()",
    )


class ProjectMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    public_id = db.Column(db.String(200), nullable=False)  # needed to delete from Cloudinary
    media_type = db.Column(db.String(20), nullable=False)  # image | video | raw

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==========================
# PUBLIC ROUTES
# ==========================
@app.route("/")
def home():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template("home.html", projects=projects)


@app.route("/projects")
def projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template("projects.html", projects=projects)


@app.route("/blog")
def blog():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template("blog.html", posts=posts)


# ==========================
# AUTH ROUTES
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():
    # if already logged in, go to admin
    if current_user.is_authenticated:
        return redirect(url_for("admin"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("admin"))

        flash("Invalid username or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout", methods=["POST", "GET"])
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))

# ==========================
# ADMIN ROUTES
# ==========================
@app.route("/admin")
@login_required
def admin():
    return render_template(
        "admin.html",
        projects=Project.query.order_by(Project.created_at.desc()).all(),
        posts=BlogPost.query.order_by(BlogPost.created_at.desc()).all(),
    )


# ---------- PROJECT ----------
@app.route("/admin/project/add", methods=["POST"])
@login_required
def add_project():
    p = Project(
        title=request.form.get("title", ""),
        description=request.form.get("description", ""),
        tech=request.form.get("tech", ""),
        github=request.form.get("github", ""),
        demo_url=request.form.get("demo_url", ""),
        has_demo=("has_demo" in request.form),
    )
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/project/delete/<int:id>", methods=["POST"])
@login_required
def delete_project(id):
    db.session.delete(Project.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/project/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_project(id):
    project = Project.query.get_or_404(id)

    if request.method == "POST":
        project.title = request.form.get("title", "")
        project.description = request.form.get("description", "")
        project.tech = request.form.get("tech", "")
        project.github = request.form.get("github", "")
        project.demo_url = request.form.get("demo_url", "")
        project.has_demo = ("has_demo" in request.form)
        db.session.commit()
        return redirect(url_for("admin"))

    return render_template("edit_project.html", project=project)


@app.route("/admin/project/upload/<int:project_id>", methods=["POST"])
@login_required
def upload_project_media(project_id):
    file = request.files.get("file")
    if not file:
        return redirect(url_for("admin"))

    # optional: accept multiple files if your form uses file input name="file" multiple
    # If you add "multiple", Flask gives a list under getlist:
    files = request.files.getlist("file")
    if not files:
        files = [file]

    for f in files:
        if not f or not getattr(f, "filename", ""):
            continue

        result = cloudinary.uploader.upload(
            f,
            resource_type="auto",
            folder="portfolio",
        )

        media = ProjectMedia(
            project_id=project_id,
            url=result["secure_url"],
            public_id=result["public_id"],
            media_type=result.get("resource_type", "image"),
        )
        db.session.add(media)

    db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/project/media/delete/<int:id>", methods=["POST"])
@login_required
def delete_project_media(id):
    media = ProjectMedia.query.get_or_404(id)

    # delete from Cloudinary first
    try:
        cloudinary.uploader.destroy(media.public_id, resource_type=media.media_type)
    except Exception:
        # don’t block UI if Cloudinary deletion fails; still remove DB row if you want
        pass

    db.session.delete(media)
    db.session.commit()
    return redirect(url_for("admin"))


# ---------- BLOG ----------
@app.route("/admin/blog/add", methods=["POST"])
@login_required
def add_blog():
    db.session.add(
        BlogPost(
            title=request.form.get("title", ""),
            body=request.form.get("body", ""),
        )
    )
    db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/blog/delete/<int:id>", methods=["POST"])
@login_required
def delete_blog(id):
    db.session.delete(BlogPost.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/blog/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_blog(id):
    post = BlogPost.query.get_or_404(id)

    if request.method == "POST":
        post.title = request.form.get("title", "")
        post.body = request.form.get("body", "")
        db.session.commit()
        return redirect(url_for("admin"))

    return render_template("edit_blog.html", post=post)


# ==========================
# INIT DB + FIRST ADMIN USER
# ==========================
def ensure_admin_user():
    """
    Creates the first admin user if none exists.
    Set these on Render Environment for production:
      ADMIN_USERNAME
      ADMIN_PASSWORD
    """
    if User.query.first():
        return

    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "changeme")

    db.session.add(
        User(
            username=username,
            password_hash=generate_password_hash(password),
        )
    )
    db.session.commit()


with app.app_context():
    db.create_all()

    # 🔧 Auto repair missing created_at column on Postgres
    from sqlalchemy import text

    try:
        db.session.execute(text("ALTER TABLE project_media ADD COLUMN IF NOT EXISTS created_at TIMESTAMP"))
        db.session.execute(text("UPDATE project_media SET created_at = NOW() WHERE created_at IS NULL"))
        db.session.commit()
    except Exception as e:
        print("DB auto-repair:", e)



if __name__ == "__main__":
    app.run(debug=True)
