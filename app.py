import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Render-safe persistent disk
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "static", "uploads"))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database (SQLite locally, PostgreSQL on Render)
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://")

DATABASE_URI = db_url or "sqlite:///portfolio.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------- MODELS ----------
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    tech = db.Column(db.String(200))
    github = db.Column(db.String(200))
    demo_url = db.Column(db.String(200))
    image = db.Column(db.String(200))
    image_url = db.Column(db.String(200))
    has_demo = db.Column(db.Boolean, default=False)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    slug = db.Column(db.String(200), unique=True)
    body = db.Column(db.Text)
    image = db.Column(db.String(200))
    created = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ---------- AUTH ----------
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "password")

# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/projects")
def projects():
    demo_projects = Project.query.filter_by(has_demo=True).all()
    code_projects = Project.query.filter_by(has_demo=False).all()
    return render_template("projects.html", demo_projects=demo_projects, code_projects=code_projects)

@app.route("/blog")
def blog():
    posts = BlogPost.query.order_by(BlogPost.created.desc()).all()
    return render_template("blog.html", posts=posts)

@app.route("/blog/<slug>")
def blog_post(slug):
    post = BlogPost.query.filter_by(slug=slug).first_or_404()
    return render_template("blog_post.html", post=post)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USER and request.form["password"] == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))
    projects = Project.query.all()
    posts = BlogPost.query.all()
    return render_template("admin.html", projects=projects, posts=posts)

@app.route("/admin/project/add", methods=["POST"])
def add_project():
    has_demo = bool(request.form.get("has_demo"))

    p = Project(
        title=request.form["title"],
        description=request.form["description"],
        tech=request.form.get("tech"),
        github=request.form.get("github"),
        demo_url=request.form.get("demo_url"),
        image=None,
        image_url=request.form.get("image_url"),
        has_demo=has_demo
    )

    db.session.add(p)
    db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/project/delete/<int:id>")
def delete_project(id):
    Project.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/blog/add", methods=["POST"])
def add_blog():
    from slugify import slugify
    image_file = request.files.get("image")
    filename = None
    if image_file and image_file.filename:
        filename = secure_filename(image_file.filename)
        image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    post = BlogPost(
        title=request.form["title"],
        slug=slugify(request.form["title"]),
        body=request.form["body"],
        image=filename
    )
    db.session.add(post)
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/blog/delete/<int:id>")
def delete_blog(id):
    BlogPost.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(debug=True)

