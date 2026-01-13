import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader
from sqlalchemy import text

# ======================
# APP SETUP
# ======================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-change-me")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "portfolio.db"))

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

# ======================
# LOGIN
# ======================
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ======================
# MODELS
# ======================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(300))
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

class ProjectMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    url = db.Column(db.String(500))
    public_id = db.Column(db.String(200))
    media_type = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

Project.media = db.relationship("ProjectMedia", cascade="all,delete-orphan", lazy=True)

@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))

# ======================
# MIGRATION AUTO-REPAIR
# ======================
def auto_repair():
    db.session.execute(text("ALTER TABLE project_media ADD COLUMN IF NOT EXISTS created_at TIMESTAMP"))
    db.session.execute(text("UPDATE project_media SET created_at = NOW() WHERE created_at IS NULL"))
    db.session.commit()

with app.app_context():
    db.create_all()
    auto_repair()

# ======================
# AUTH ROUTES
# ======================
@app.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin"))
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            return redirect(url_for("admin"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ======================
# PUBLIC
# ======================
@app.route("/")
def home():
    return render_template("home.html", projects=Project.query.order_by(Project.created_at.desc()).all())

@app.route("/projects")
def projects():
    return render_template("projects.html", projects=Project.query.order_by(Project.created_at.desc()).all())

@app.route("/blog")
def blog():
    return render_template("blog.html", posts=BlogPost.query.order_by(BlogPost.created_at.desc()).all())

# ======================
# ADMIN
# ======================
@app.route("/admin")
@login_required
def admin():
    return render_template("admin.html",
        projects=Project.query.order_by(Project.created_at.desc()).all(),
        posts=BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    )
@app.route("/admin/project/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_project(id):
    project = Project.query.get_or_404(id)

    if request.method == "POST":
        project.title = request.form["title"]
        project.description = request.form["description"]
        project.tech = request.form["tech"]
        project.github = request.form["github"]
        project.demo_url = request.form["demo_url"]
        project.has_demo = "has_demo" in request.form
        db.session.commit()
        return redirect(url_for("admin"))

    return render_template("edit_project.html", project=project)

@app.route("/admin/project/add", methods=["POST"])
@login_required
def add_project():
    p = Project(
        title=request.form["title"],
        description=request.form["description"],
        tech=request.form["tech"],
        github=request.form["github"],
        demo_url=request.form["demo_url"],
        has_demo="has_demo" in request.form
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

@app.route("/admin/project/upload/<int:pid>", methods=["POST"])
@login_required
def upload_media(pid):
    for f in request.files.getlist("file"):
        if not f: continue
        r = cloudinary.uploader.upload(f, resource_type="auto", folder="portfolio")
        db.session.add(ProjectMedia(
            project_id=pid,
            url=r["secure_url"],
            public_id=r.get("public_id"),
            media_type=r.get("resource_type","image")
        ))
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/project/media/delete/<int:id>", methods=["POST"])
@login_required
def delete_media(id):
    m = ProjectMedia.query.get_or_404(id)
    if m.public_id:
        try: cloudinary.uploader.destroy(m.public_id, resource_type="auto")
        except: pass
    db.session.delete(m)
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/cleanup-media")
@login_required
def cleanup():
    bad = ProjectMedia.query.filter(
        (ProjectMedia.public_id==None)|(ProjectMedia.public_id=="")|(ProjectMedia.url==None)|(ProjectMedia.url=="")
    ).all()
    for b in bad: db.session.delete(b)
    db.session.commit()
    return f"Removed {len(bad)} broken rows"

@app.route("/admin/blog/add", methods=["POST"])
@login_required
def add_blog():
    db.session.add(BlogPost(title=request.form["title"], body=request.form["body"]))
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/blog/delete/<int:id>", methods=["POST"])
@login_required
def delete_blog(id):
    db.session.delete(BlogPost.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for("admin"))


@app.route("/admin/blog/edit/<int:id>", methods=["GET","POST"])
@login_required
def edit_blog(id):
    post = BlogPost.query.get_or_404(id)
    if request.method == "POST":
        post.title = request.form["title"]
        post.body = request.form["body"]
        db.session.commit()
        return redirect(url_for("admin"))
    return render_template("edit_blog.html", post=post)

# ======================
# FIRST ADMIN AUTO-CREATE
# ======================
with app.app_context():
    if not User.query.first():
        db.session.add(User(
            username=os.getenv("ADMIN_USERNAME","admin"),
            password_hash=generate_password_hash(os.getenv("ADMIN_PASSWORD","changeme"))
        ))
        db.session.commit()

if __name__ == "__main__":
    app.run()
