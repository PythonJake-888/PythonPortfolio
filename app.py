import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename

# ---------- APP SETUP ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
DATABASE = os.path.join(BASE_DIR, "instance", "portfolio.db")

app = Flask(__name__)
app.secret_key = "dev-secret"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- AUTH ----------
ADMIN_USER = "admin"
ADMIN_PASS = "password"

# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/projects")
def projects():
    conn = get_db()
    demo_projects = conn.execute(
        "SELECT * FROM projects WHERE has_demo = 1"
    ).fetchall()
    code_projects = conn.execute(
        "SELECT * FROM projects WHERE has_demo = 0"
    ).fetchall()
    conn.close()

    return render_template(
        "projects.html",
        demo_projects=demo_projects,
        code_projects=code_projects
    )

@app.route("/blog")
def blog():
    return render_template("blog.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USER and request.form["password"] == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = get_db()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return render_template("admin.html", projects=projects)

@app.route("/admin/add", methods=["POST"])
def add_project():
    title = request.form.get("title")
    description = request.form.get("description")
    tech = request.form.get("tech")
    github = request.form.get("github")
    demo_url = request.form.get("demo_url")
    image_url = request.form.get("image_url")
    has_demo = 1 if request.form.get("has_demo") else 0

    conn = sqlite3.connect("projects.db")
    conn.execute(
        """
        INSERT INTO projects
        (title, description, tech, github, demo_url, image_url, has_demo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (title, description, tech, github, demo_url, image_url, has_demo)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))



@app.route("/admin/edit/<int:id>")
def edit_project(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = get_db()
    project = conn.execute(
        "SELECT * FROM projects WHERE id = ?", (id,)
    ).fetchone()
    conn.close()

    return render_template("edit_project.html", project=project)

@app.route("/admin/update/<int:id>", methods=["POST"])
def update_project(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    image_file = request.files.get("image")
    image_name = request.form.get("current_image")

    if image_file and image_file.filename:
        image_name = secure_filename(image_file.filename)
        image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_name))

    has_demo = 1 if request.form.get("has_demo") else 0

    conn = get_db()
    image_url = request.form.get("image_url")

    conn.execute(
        """
        UPDATE projects
        SET title=?, description=?, tech=?, github=?,
            demo_url=?, image=?, image_url=?, has_demo=?
        WHERE id=?
        """,
        (
            request.form["title"],
            request.form["description"],
            request.form["tech"],
            request.form["github"],
            request.form.get("demo_url"),
            image_name,
            image_url,
            has_demo,
            id,
        ),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))

@app.route("/admin/delete/<int:id>", methods=["POST"])
def delete_project(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(debug=True)
