from flask import Flask, render_template
from flask import request
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "instance", "portfolio.db")

app = Flask(__name__)

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_posts_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

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

# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/projects", methods=["GET", "POST"])
def projects():
    conn = get_db()

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        tech = request.form["tech"]
        github = request.form["github"]

        conn.execute(
            "INSERT INTO projects (title, description, tech, github) VALUES (?, ?, ?, ?)",
            (title, description, tech, github)
        )
        conn.commit()

    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()

    return render_template("projects.html", projects=projects)


@app.route("/blog")
def blog():
    conn = get_db()
    posts = conn.execute("SELECT * FROM posts").fetchall()
    conn.close()
    return render_template("blog.html", posts=posts)


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")



def seed_projects():
    conn = get_db()
    conn.execute(
        "INSERT INTO projects (title, description, tech, github) VALUES (?, ?, ?, ?)",
        ("WeatherWake",
         "GUI app that displays live weather data using an external API.",
         "Python, API, GUI",
         "#")
    )
    conn.execute(
        "INSERT INTO projects (title, description, tech, github) VALUES (?, ?, ?, ?)",
        ("Pokemon RPG",
         "Turn-based RPG inspired by Pokémon with combat and inventory systems.",
         "Python, Pygame",
         "#")
    )
    conn.commit()
    conn.close()

# ---------- RUN ----------
if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    #init_db()
    #init_posts_table()
    app.run(debug=True)
