import os
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash)
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "changeme_college_project")

# ─────────────────────────── DB CONNECTION ───────────────────────────
def get_db():
    db_url = os.environ.get("DATABASE_URL")
    # Fix for Render/Heroku postgres dialect
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    if not db_url:
        raise ValueError("DATABASE_URL is not set in Environment Variables")

    # Connect with RealDictCursor so we can use row['column_name']
    conn = psycopg2.connect(
        db_url, 
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    conn.autocommit = True 
    return conn

# ─────────────────────────── HELPERS ───────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            flash("Admin access required.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────── ROUTES ───────────────────────────
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        phone    = request.form.get("phone", "").strip()
        dept     = request.form.get("department", "").strip()
        year     = request.form.get("class_year", "").strip()
        roll     = request.form.get("roll_no", "").strip()
        loc      = request.form.get("college_location", "").strip()
        pwd      = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not all([name, email, phone, pwd]):
            flash("Missing required fields.", "error")
            return render_template("register.html")

        if pwd != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        hashed = generate_password_hash(pwd)
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("""INSERT INTO users (name, email, phone, department, class_year, roll_no, college_location, password)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (name, email, phone, dept, year, roll, loc, hashed))
            flash("Registration successful!", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
        finally:
            cur.close(); conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        pwd = request.form.get("password", "")
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user and check_password_hash(user["password"], pwd):
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ─────────────────────────── ADMIN SECTION ───────────────────────────

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # BYPASS: Always works with admin / admin123
        if username == "admin" and password == "admin123":
            session["admin_id"] = 1
            session["admin_username"] = "admin"
            return redirect(url_for("admin_dashboard"))
        
        flash("Invalid admin credentials.", "error")
    return render_template("admin_login.html")

@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():
    conn = get_db()
    cur = conn.cursor()
    all_reqs = []
    try:
        # Using LEFT JOIN to prevent crashes if records are missing
        cur.execute("""
            SELECT pr.*, u.name as user_name, e.item_name 
            FROM pickup_requests pr
            LEFT JOIN users u ON pr.user_id = u.user_id
            LEFT JOIN ewaste_items e ON pr.waste_id = e.waste_id
            ORDER BY pr.created_at DESC
        """)
        all_reqs = cur.fetchall()
    except Exception as e:
        print(f"Dashboard Error: {e}")
    finally:
        cur.close(); conn.close()

    pending = [r for r in all_reqs if r.get('status') == 'Pending']
    completed = [r for r in all_reqs if r.get('status') == 'Completed']
    cancelled = [r for r in all_reqs if r.get('status') == 'Cancelled']
    
    # Also pass assigned/picked up categories if your template uses them
    assigned = [r for r in all_reqs if r.get('status') == 'Assigned']

    return render_template("admin_dashboard.html", 
                           pending=pending, 
                           completed=completed, 
                           cancelled=cancelled,
                           assigned=assigned)

@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

# ─────────────────────────── DATA HANDLING ───────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        SELECT pr.*, e.item_name FROM pickup_requests pr
        JOIN ewaste_items e ON pr.waste_id = e.waste_id
        WHERE pr.user_id=%s ORDER BY pr.created_at DESC
    """, (uid,))
    history = cur.fetchall()
    cur.close(); conn.close()
    return render_template("dashboard.html", history=history, active=[])

# ─────────────────────────── RUN ───────────────────────────
if __name__ == "__main__":
    # Ensure tables exist on startup
    try:
        from init_db import create_tables
        create_tables()
    except:
        pass
    app.run()
