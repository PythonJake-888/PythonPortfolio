import sqlite3
import os


from flask import Flask, render_template, request, redirect, url_for


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "instance", "portfolio.db")

app = Flask(__name__)

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            tech TEXT,
            github TEXT
        )
    """)
    conn.commit()
    conn.close()

# ---------- PUBLIC ROUTES ----------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/projects")
def projects():
    conn = get_db()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return render_template("projects.html", projects=projects)

@app.route("/blog")
def blog():
    return render_template("blog.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# ---------- ADMIN ROUTES ----------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    conn = get_db()

    if request.method == "POST":
        conn.execute(
            "INSERT INTO projects (title, description, tech, github) VALUES (?, ?, ?, ?)",
            (
                request.form["title"],
                request.form["description"],
                request.form["tech"],
                request.form["github"]
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin"))

    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return render_template("admin.html", projects=projects)

@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def edit_project(id):
    conn = get_db()

    if request.method == "POST":
        conn.execute(
            """
            UPDATE projects
            SET title = ?, description = ?, tech = ?, github = ?
            WHERE id = ?
            """,
            (
                request.form["title"],
                request.form["description"],
                request.form["tech"],
                request.form["github"],
                id
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin"))

    project = conn.execute(
        "SELECT * FROM projects WHERE id = ?", (id,)
    ).fetchone()
    conn.close()

    return render_template("edit_project.html", project=project)

@app.route("/admin/delete/<int:id>")
def delete_project(id):
    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

# ---------- RUN ----------
if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    init_db()
    app.run(debug=True)
