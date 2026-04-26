import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "shubham_ewaste_2026")

# ─────────────────────────── DATABASE SYSTEM ───────────────────────────

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    # Fixes the Render postgres prefix issue
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = True
    return conn

def auto_setup_db():
    """Builds your college project tables automatically."""
    conn = get_db()
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
            collector_name TEXT,
            collector_phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            cancelled_at TIMESTAMP
        );
    """)
    cur.close()
    conn.close()

# ─────────────────────────── USER ROUTES ───────────────────────────

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form
        hashed = generate_password_hash(data.get("password"))
        conn = get_db(); cur = conn.cursor()
        try:
            cur.execute("""INSERT INTO users (name, email, phone, department, class_year, roll_no, college_location, password)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (data.get("name"), data.get("email"), data.get("phone"), data.get("department"), 
                         data.get("class_year"), data.get("roll_no"), data.get("college_location"), hashed))
            flash("Registration Successful!", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error: {e}", "error")
        finally:
            cur.close(); conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email, pwd = request.form.get("email"), request.form.get("password")
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user and check_password_hash(user["password"], pwd):
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Invalid Credentials", "error")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session: return redirect(url_for("login"))
    uid = session["user_id"]
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pickup_requests WHERE user_id = %s", (uid,))
    reqs = cur.fetchall()
    cur.close(); conn.close()
    return render_template("dashboard.html", active=reqs, history=reqs)

# ─────────────────────────── ADMIN ROUTES ───────────────────────────

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u, p = request.form.get("username"), request.form.get("password")
        # Hardcoded bypass for the college presentation
        if u == "admin" and p == "admin123":
            session["admin_id"] = 1
            return redirect(url_for("admin_dashboard"))
        flash("Invalid Admin Login", "error")
    return render_template("admin_login.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin_id" not in session: return redirect(url_for("admin_login"))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pickup_requests ORDER BY created_at DESC")
    reqs = cur.fetchall()
    cur.close(); conn.close()
    
    # Matching every variable your template might need
    return render_template("admin_dashboard.html", 
                           pending=[r for r in reqs if r['status'] == 'Pending'],
                           assigned=[r for r in reqs if r['status'] == 'Assigned'],
                           completed=[r for r in reqs if r['status'] == 'Completed'],
                           cancelled=[r for r in reqs if r['status'] == 'Cancelled'],
                           picked_up=[], recycling=[])

@app.route("/reports")
def reports():
    return render_template("reports.html", total_users=0, total_items=0, category_stats=[], monthly=[])

@app.route("/logout")
@app.route("/admin_logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# Keep these empty to satisfy url_for in templates
@app.route("/add_waste")
def add_waste(): return render_template("add_waste.html")
@app.route("/request_pickup")
def request_pickup(): return render_template("request_pickup.html")
@app.route("/cancel_request/<int:request_id>", methods=["POST"])
def cancel_request(request_id): return redirect(url_for("dashboard"))
@app.route("/update_status/<int:request_id>", methods=["POST"])
def update_status(request_id): return redirect(url_for("admin_dashboard"))
@app.route("/assign_collector/<int:request_id>", methods=["POST"])
def assign_collector(request_id): return redirect(url_for("admin_dashboard"))

# ─────────────────────────── STARTUP ───────────────────────────

if __name__ == "__main__":
    try:
        auto_setup_db()
    except Exception as e:
        print(f"DB Setup Skip: {e}")
    app.run(host="0.0.0.0", port=10000)
