import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "college_project_2026")

# ─────────────────────────── DATABASE SETUP ───────────────────────────

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = True
    return conn

def init_db():
    """Builds the tables automatically if they don't exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            department TEXT,
            class_year TEXT,
            roll_no TEXT,
            college_location TEXT,
            password TEXT
        );
        CREATE TABLE IF NOT EXISTS ewaste_items (
            waste_id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            item_name TEXT,
            category TEXT,
            quantity INTEGER,
            waste_condition TEXT,
            approx_weight TEXT,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS pickup_requests (
            request_id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            waste_id INTEGER REFERENCES ewaste_items(waste_id),
            pickup_location TEXT,
            pickup_date DATE,
            time_slot TEXT,
            note TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.close()
    conn.close()

# ─────────────────────────── ROUTES ───────────────────────────

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Hardcoded for guaranteed access
        if username == "admin" and password == "admin123":
            session["admin_id"] = 1
            session["admin_username"] = "admin"
            return redirect(url_for("admin_dashboard"))
        flash("Invalid Credentials")
    return render_template("admin_login.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pickup_requests ORDER BY created_at DESC")
    reqs = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template("admin_dashboard.html", pending=reqs, completed=[], cancelled=[])

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Simplified for testing
        name = request.form.get("name")
        email = request.form.get("email")
        pwd = request.form.get("password")
        
        hashed = generate_password_hash(pwd)
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed))
            flash("Success!")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error: {e}")
        finally:
            cur.close()
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        pwd = request.form.get("password")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and check_password_hash(user["password"], pwd):
            session["user_id"] = user["user_id"]
            return redirect(url_for("home"))
    return render_template("login.html")

# ─────────────────────────── STARTUP ───────────────────────────

if __name__ == "__main__":
    try:
        init_db()
    except:
        pass
    app.run(host="0.0.0.0", port=10000)
