import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def create_tables():
    commands = [
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100) UNIQUE,
            phone VARCHAR(20),
            department VARCHAR(100),
            class_year VARCHAR(20),
            roll_no VARCHAR(20),
            college_location VARCHAR(255),
            password VARCHAR(255)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ewaste_items (
            waste_id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            item_name VARCHAR(100),
            category VARCHAR(50),
            quantity INTEGER,
            waste_condition VARCHAR(100),
            approx_weight VARCHAR(50),
            description TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS pickup_requests (
            request_id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(user_id),
            waste_id INTEGER REFERENCES ewaste_items(waste_id),
            pickup_location TEXT,
            pickup_date DATE,
            time_slot VARCHAR(50),
            note TEXT,
            status VARCHAR(50) DEFAULT 'Pending',
            collector_name VARCHAR(100),
            collector_phone VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assigned_at TIMESTAMP,
            picked_up_at TIMESTAMP,
            completed_at TIMESTAMP,
            cancelled_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS admin (
            admin_id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password VARCHAR(255)
        )
        """,
        # This adds the default admin ONLY if it doesn't exist
        """
        INSERT INTO admin (username, password) 
        SELECT 'admin', 'scrypt:32768:8:1$C2A0b0A1$377f886f32e9877708573215286209210967a57c5031b674843475f492b436923c8e762c9339e3b4a243d671569055452f1f0a597e748809e259e21820577663'
        WHERE NOT EXISTS (SELECT 1 FROM admin WHERE username = 'admin');
        """
    ]
    
    conn = None
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cur = conn.cursor()
        for command in commands:
            cur.execute(command)
        cur.close()
        conn.commit()
        print("Tables created successfully!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    create_tables()
