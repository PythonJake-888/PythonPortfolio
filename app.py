import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "portfolio.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

cloudinary.config(
    cloud_name="dlfw0pag",
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# ================= MODELS =================

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    tech = db.Column(db.String(200))
    github = db.Column(db.String(300))
    demo_url = db.Column(db.String(300))
    has_demo = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    media = db.relationship("ProjectMedia", backref="project", lazy=True, cascade="all,delete")

class ProjectMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    url = db.Column(db.String(500))
    media_type = db.Column(db.String(20))

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ================= ROUTES =================

@app.route("/")
def home():
    return render_template("home.html", projects=Project.query.all())

@app.route("/projects")
def projects():
    return render_template("projects.html", projects=Project.query.all())

@app.route("/blog")
def blog():
    return render_template("blog.html", posts=BlogPost.query.all())

@app.route("/admin")
def admin():
    return render_template("admin.html", projects=Project.query.all(), posts=BlogPost.query.all())

# ---------- PROJECT ----------

@app.route("/admin/project/add", methods=["POST"])
def add_project():
    p = Project(
        title=request.form["title"],
        description=request.form["description"],
        tech=request.form["tech"],
        github=request.form["github"],
        demo_url=request.form["demo_url"],
        has_demo="has_demo" in request.form,
    )
    db.session.add(p)
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/project/delete/<int:id>", methods=["POST"])
def delete_project(id):
    db.session.delete(Project.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/project/upload/<int:project_id>", methods=["POST"])
def upload_project_media(project_id):
    file = request.files["file"]

    result = cloudinary.uploader.upload(file, resource_type="auto", folder="portfolio")

    media = ProjectMedia(
        project_id=project_id,
        url=result["secure_url"],
        media_type=result["resource_type"],
    )

    db.session.add(media)
    db.session.commit()
    return redirect(url_for("admin"))
@app.route("/admin/project/edit/<int:id>", methods=["GET", "POST"])
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

# ---------- BLOG ----------

@app.route("/admin/blog/add", methods=["POST"])
def add_blog():
    db.session.add(BlogPost(title=request.form["title"], body=request.form["body"]))
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/blog/delete/<int:id>", methods=["POST"])
def delete_blog(id):
    db.session.delete(BlogPost.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/blog/edit/<int:id>", methods=["GET", "POST"])
def edit_blog(id):
    post = BlogPost.query.get_or_404(id)
    if request.method == "POST":
        post.title = request.form["title"]
        post.body = request.form["body"]
        db.session.commit()
        return redirect(url_for("admin"))
    return render_template("edit_blog.html", post=post)

# ================= INIT =================

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
