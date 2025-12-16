from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "instance", "portfolio.db")

app = Flask(__name__)
app.secret_key = "dev-secret-key"


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
            title TEXT NOT NULL,
            description TEXT,
            tech TEXT,
            github TEXT
        )
    """)
    conn.commit()
    conn.close()

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
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return render_template("projects.html", projects=projects)

@app.route("/blog")
def blog():
    return render_template("blog.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form.get("username") == ADMIN_USER
            and request.form.get("password") == ADMIN_PASS
        ):
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
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
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute(
        "INSERT INTO projects (title, description, tech, github) VALUES (?, ?, ?, ?)",
        (
            request.form["title"],
            request.form["description"],
            request.form["tech"],
            request.form["github"],
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

@app.route("/admin/delete/<int:id>")
def delete_project(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

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
