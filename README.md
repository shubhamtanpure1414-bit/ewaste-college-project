# ♻ EWaste College Management System

A Flask + MySQL web application for managing e-waste collection in a college environment. Students, faculty, and staff can log their old electronics and schedule pickups. Admins can manage requests, assign collectors, and track recycling progress.

---

## 🗂 Project Structure

```
ewaste_college/
├── app.py                  # Main Flask application
├── database.sql            # MySQL schema + default admin
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── README.md
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── home.html
    ├── register.html
    ├── login.html
    ├── dashboard.html
    ├── add_waste.html
    ├── request_pickup.html
    ├── admin_login.html
    ├── admin_dashboard.html
    └── reports.html
```

---

## ⚙️ Setup Instructions

### 1. Clone / Download the project

```bash
cd /path/to/your/projects
# place the ewaste_college folder here
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up MySQL database

```bash
mysql -u root -p < database.sql
```

### 4. Create your `.env` file

```bash
cp .env.example .env
```

Then edit `.env` and fill in your MySQL password:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=ewaste_college_db
SECRET_KEY=any_long_random_string_here
```

### 5. Run the app

```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

---

## 🔑 Default Admin Credentials

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |
| URL      | `/admin_login` |

---

## 👤 User Workflow

```
Register → Login → Add E-Waste Item → Request Pickup
→ Admin assigns collector → Admin updates status
→ When Completed → Appears in Pickup History
```

## 🛡 Admin Workflow

```
Admin Login → View all requests by status →
Assign collector → Update status (Pending → Assigned →
Picked Up → Sent To Recycling → Completed)
→ View Reports
```

---

## 🌐 Routes

| Route | Description |
|---|---|
| `/` | Home page |
| `/register` | User registration |
| `/login` | User login |
| `/logout` | User logout |
| `/dashboard` | User dashboard |
| `/add_waste` | Add e-waste item |
| `/request_pickup` | Request a pickup |
| `/cancel_request/<id>` | Cancel pending request |
| `/admin_login` | Admin login |
| `/admin_logout` | Admin logout |
| `/admin_dashboard` | Admin dashboard |
| `/update_status/<id>` | Update request status |
| `/assign_collector/<id>` | Assign pickup collector |
| `/reports` | Admin reports |

---

## 📦 Tech Stack

- **Backend**: Python Flask
- **Database**: MySQL (mysql-connector-python)
- **Auth**: Werkzeug password hashing + Flask sessions
- **Frontend**: HTML5, CSS3 (no frameworks)
- **Env**: python-dotenv
