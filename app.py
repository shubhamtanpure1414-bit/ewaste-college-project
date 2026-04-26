import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "college_project_final_fix")

# ─────────────────────────── DATABASE ───────────────────────────

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = True
    return conn

# ─────────────────────────── HELPERS ───────────────────────────

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session: return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────── MAIN ROUTES ───────────────────────────

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        pwd = request.form.get("password")
        hashed = generate_password_hash(pwd)
        conn = get_db(); cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed))
            flash("Registration successful!")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error: {e}")
        finally:
            cur.close(); conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        pwd = request.form.get("password")
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user and check_password_hash(user["password"], pwd):
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Invalid login")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ─────────────────────────── USER PAGES ───────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pickup_requests WHERE user_id = %s", (uid,))
    reqs = cur.fetchall()
    cur.close(); conn.close()
    return render_template("dashboard.html", active=reqs, history=[])

@app.route("/add_waste", methods=["GET", "POST"])
@login_required
def add_waste():
    return render_template("add_waste.html")

@app.route("/request_pickup", methods=["GET", "POST"])
@login_required
def request_pickup():
    return render_template("request_pickup.html", items=[])

# ─────────────────────────── ADMIN SECTION ───────────────────────────

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        if u == "admin" and p == "admin123":
            session["admin_id"] = 1
            return redirect(url_for("admin_dashboard"))
        flash("Invalid Admin Credentials")
    return render_template("admin_login.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session: return redirect(url_for("admin_login"))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pickup_requests")
    reqs = cur.fetchall()
    cur.close(); conn.close()
    return render_template("admin_dashboard.html", pending=reqs, completed=[], cancelled=[], assigned=[], picked_up=[], recycling=[])

@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/reports")
def reports():
    return render_template("reports.html", total_users=0, total_items=0, total_pending=0, total_completed=0, total_cancelled=0, category_stats=[], monthly=[])

# ─────────────────────────── STARTUP ───────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
