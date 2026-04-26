import os
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash)
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "changeme_secret")

# ─────────────────────────── DB ───────────────────────────
def get_db():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL"),
        cursor_factory=psycopg2.extras.RealDictCursor
    )

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

# ─────────────────────────── HOME ───────────────────────────
@app.route("/")
def home():
    return render_template("home.html")

# ─────────────────────────── REGISTER ───────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name      = request.form.get("name", "").strip()
        email     = request.form.get("email", "").strip()
        phone     = request.form.get("phone", "").strip()
        dept      = request.form.get("department", "").strip()
        cls_year  = request.form.get("class_year", "").strip()
        roll_no   = request.form.get("roll_no", "").strip()
        location  = request.form.get("college_location", "").strip()
        password  = request.form.get("password", "")
        confirm   = request.form.get("confirm_password", "")

        if not all([name, email, phone, password]):
            flash("Name, email, phone and password are required.", "error")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        hashed = generate_password_hash(password)
        db = get_db()
        cur = db.cursor()
        try:
            cur.execute(
                """INSERT INTO users
                   (name, email, phone, department, class_year, roll_no, college_location, password)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (name, email, phone, dept, cls_year, roll_no, location, hashed)
            )
            db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except psycopg2.IntegrityError:
            db.rollback()
            flash("Email already registered.", "error")
        finally:
            cur.close()
            db.close()

    return render_template("register.html")

# ─────────────────────────── LOGIN ───────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        db.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"]   = user["user_id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ─────────────────────────── USER DASHBOARD ───────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT pr.request_id, e.item_name, e.category, e.quantity,
               pr.pickup_location, pr.pickup_date, pr.time_slot, pr.status
        FROM pickup_requests pr
        JOIN ewaste_items e ON pr.waste_id = e.waste_id
        WHERE pr.user_id=%s AND pr.status NOT IN ('Completed','Cancelled')
        ORDER BY pr.created_at DESC
    """, (uid,))
    active = cur.fetchall()

    cur.execute("""
        SELECT e.item_name, e.category, e.quantity,
               pr.pickup_date, pr.completed_at, pr.status
        FROM pickup_requests pr
        JOIN ewaste_items e ON pr.waste_id = e.waste_id
        WHERE pr.user_id=%s AND pr.status='Completed'
        ORDER BY pr.completed_at DESC
    """, (uid,))
    history = cur.fetchall()

    cur.close()
    db.close()
    return render_template("dashboard.html", active=active, history=history)

# ─────────────────────────── ADD WASTE ───────────────────────────
@app.route("/add_waste", methods=["GET", "POST"])
@login_required
def add_waste():
    if request.method == "POST":
        uid         = session["user_id"]
        item_name   = request.form.get("item_name", "").strip()
        category    = request.form.get("category", "").strip()
        quantity    = request.form.get("quantity", 1)
        condition   = request.form.get("waste_condition", "").strip()
        weight      = request.form.get("approx_weight", None) or None
        description = request.form.get("description", "").strip()

        if not all([item_name, category, quantity]):
            flash("Item name, category and quantity are required.", "error")
            return render_template("add_waste.html")

        db = get_db()
        cur = db.cursor()
        cur.execute(
            """INSERT INTO ewaste_items
               (user_id, item_name, category, quantity, waste_condition, approx_weight, description)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (uid, item_name, category, quantity, condition, weight, description)
        )
        db.commit()
        cur.close()
        db.close()
        flash("E-Waste item added successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_waste.html")

# ─────────────────────────── REQUEST PICKUP ───────────────────────────
@app.route("/request_pickup", methods=["GET", "POST"])
@login_required
def request_pickup():
    uid = session["user_id"]
    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        waste_id  = request.form.get("waste_id")
        location  = request.form.get("pickup_location", "").strip()
        date      = request.form.get("pickup_date", "")
        time_slot = request.form.get("time_slot", "").strip()
        note      = request.form.get("note", "").strip()

        if not all([waste_id, location, date]):
            flash("Item, pickup location and date are required.", "error")
        else:
            cur.execute(
                """INSERT INTO pickup_requests
                   (user_id, waste_id, pickup_location, pickup_date, time_slot, note)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (uid, waste_id, location, date, time_slot, note)
            )
            db.commit()
            cur.close()
            db.close()
            flash("Your pickup request has been sent to admin.", "success")
            return redirect(url_for("dashboard"))

    cur.execute(
        "SELECT waste_id, item_name, category FROM ewaste_items WHERE user_id=%s",
        (uid,)
    )
    items = cur.fetchall()
    cur.close()
    db.close()
    return render_template("request_pickup.html", items=items)

# ─────────────────────────── CANCEL REQUEST ───────────────────────────
@app.route("/cancel_request/<int:request_id>", methods=["POST"])
@login_required
def cancel_request(request_id):
    uid = session["user_id"]
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM pickup_requests WHERE request_id=%s AND user_id=%s",
                (request_id, uid))
    req = cur.fetchone()
    if req and req["status"] == "Pending":
        cur.execute(
            "UPDATE pickup_requests SET status='Cancelled', cancelled_at=NOW() WHERE request_id=%s",
            (request_id,)
        )
        db.commit()
        flash("Request cancelled successfully.", "success")
    else:
        flash("Only pending requests can be cancelled.", "error")
    cur.close()
    db.close()
    return redirect(url_for("dashboard"))

# ─────────────────────────── ADMIN LOGIN ───────────────────────────
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM admin WHERE username=%s", (username,))
        admin = cur.fetchone()
        cur.close()
        db.close()

        if admin and check_password_hash(admin["password"], password):
            session["admin_id"]       = admin["admin_id"]
            session["admin_username"] = admin["username"]
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.", "error")

    return render_template("admin_login.html")

@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

# ─────────────────────────── ADMIN DASHBOARD ───────────────────────────
@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():
    db = get_db()
    cur = db.cursor()

    base_q = """
        SELECT pr.*, u.name, u.email, u.phone, u.department, u.roll_no,
               e.item_name, e.category, e.quantity, e.waste_condition,
               e.approx_weight
        FROM pickup_requests pr
        JOIN users u ON pr.user_id = u.user_id
        JOIN ewaste_items e ON pr.waste_id = e.waste_id
        WHERE pr.status=%s
        ORDER BY pr.created_at DESC
    """

    def fetch(status):
        cur.execute(base_q, (status,))
        return cur.fetchall()

    pending    = fetch("Pending")
    assigned   = fetch("Assigned")
    picked_up  = fetch("Picked Up")
    recycling  = fetch("Sent To Recycling")
    completed  = fetch("Completed")
    cancelled  = fetch("Cancelled")

    cur.close()
    db.close()
    return render_template("admin_dashboard.html",
        pending=pending, assigned=assigned, picked_up=picked_up,
        recycling=recycling, completed=completed, cancelled=cancelled)

# ─────────────────────────── UPDATE STATUS ───────────────────────────
@app.route("/update_status/<int:request_id>", methods=["POST"])
@admin_required
def update_status(request_id):
    status = request.form.get("status")
    db = get_db()
    cur = db.cursor()

    if status == "Completed":
        cur.execute(
            "UPDATE pickup_requests SET status=%s, completed_at=NOW() WHERE request_id=%s",
            (status, request_id)
        )
    elif status == "Cancelled":
        cur.execute(
            "UPDATE pickup_requests SET status=%s, cancelled_at=NOW() WHERE request_id=%s",
            (status, request_id)
        )
    else:
        cur.execute(
            "UPDATE pickup_requests SET status=%s WHERE request_id=%s",
            (status, request_id)
        )

    db.commit()
    cur.close()
    db.close()
    flash(f"Request #{request_id} updated to '{status}'.", "success")
    return redirect(url_for("admin_dashboard"))

# ─────────────────────────── ASSIGN COLLECTOR ───────────────────────────
@app.route("/assign_collector/<int:request_id>", methods=["POST"])
@admin_required
def assign_collector(request_id):
    name  = request.form.get("collector_name", "").strip()
    phone = request.form.get("collector_phone", "").strip()

    if not name:
        flash("Collector name is required.", "error")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    cur = db.cursor()
    cur.execute(
        """UPDATE pickup_requests
           SET collector_name=%s, collector_phone=%s,
               assigned_at=NOW(), status='Assigned'
           WHERE request_id=%s""",
        (name, phone, request_id)
    )
    db.commit()
    cur.close()
    db.close()
    flash(f"Collector assigned to Request #{request_id}.", "success")
    return redirect(url_for("admin_dashboard"))

# ─────────────────────────── REPORTS ───────────────────────────
@app.route("/reports")
@admin_required
def reports():
    db = get_db()
    cur = db.cursor()

    def scalar(q, params=()):
        cur.execute(q, params)
        row = cur.fetchone()
        return list(row.values())[0] if row else 0

    total_users     = scalar("SELECT COUNT(*) FROM users")
    total_items     = scalar("SELECT COUNT(*) FROM ewaste_items")
    total_pending   = scalar("SELECT COUNT(*) FROM pickup_requests WHERE status='Pending'")
    total_completed = scalar("SELECT COUNT(*) FROM pickup_requests WHERE status='Completed'")
    total_cancelled = scalar("SELECT COUNT(*) FROM pickup_requests WHERE status='Cancelled'")

    cur.execute("""
        SELECT category, COUNT(*) as count, SUM(quantity) as total_qty
        FROM ewaste_items GROUP BY category ORDER BY total_qty DESC
    """)
    category_stats = cur.fetchall()

    cur.execute("""
        SELECT TO_CHAR(completed_at, 'YYYY-MM') as month,
               COUNT(*) as count
        FROM pickup_requests
        WHERE status='Completed' AND completed_at IS NOT NULL
        GROUP BY month ORDER BY month DESC LIMIT 12
    """)
    monthly = cur.fetchall()

    cur.close()
    db.close()
    return render_template("reports.html",
        total_users=total_users, total_items=total_items,
        total_pending=total_pending, total_completed=total_completed,
        total_cancelled=total_cancelled,
        category_stats=category_stats, monthly=monthly)

# ─────────────────────────── RUN ───────────────────────────
if __name__ == "__main__":
    app.run()
