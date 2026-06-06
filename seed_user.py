import sys
import random
from datetime import datetime

sys.path.insert(0, ".")
from database.db import get_db, init_db
from werkzeug.security import generate_password_hash

first_names = [
    "Arjun", "Rohan", "Vikram", "Karan", "Rahul", "Amit", "Suresh", "Anil",
    "Deepak", "Rajesh", "Priya", "Sneha", "Ananya", "Divya", "Kavya", "Pooja",
    "Meera", "Lakshmi", "Sunita", "Rekha", "Aarav", "Ishaan", "Vivaan",
    "Aditya", "Siddharth", "Riya", "Saanvi", "Aadhya", "Kritika", "Nisha",
    "Harish", "Venkatesh", "Subramaniam", "Krishnan", "Murugan", "Anand",
    "Balaji", "Ravi", "Senthil", "Karthik", "Preethi", "Bhavana", "Saranya",
    "Revathi", "Vignesh", "Akash", "Nikhil", "Gaurav", "Manish", "Varun"
]

last_names = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Shah", "Mehta",
    "Joshi", "Nair", "Pillai", "Menon", "Iyer", "Rao", "Reddy", "Naidu",
    "Krishnamurthy", "Subramanian", "Venkataraman", "Balasubramanian",
    "Chatterjee", "Banerjee", "Mukherjee", "Das", "Bose", "Sen", "Ghosh",
    "Desai", "Kulkarni", "Patil", "Shinde", "Jadhav", "More",
    "Kapoor", "Malhotra", "Chopra", "Bhatia", "Arora", "Khanna",
    "Pandey", "Mishra", "Tripathi", "Dwivedi", "Shukla", "Tiwari"
]

init_db()

conn = get_db()
try:
    for _ in range(100):
        first = random.choice(first_names)
        last = random.choice(last_names)
        name = f"{first} {last}"

        suffix = random.randint(10, 999)
        email_local = f"{first.lower()}{last.lower()[:4]}{suffix}"
        email = f"{email_local}@gmail.com"

        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            continue

        password_hash = generate_password_hash("password123")
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (name, email, password_hash, created_at)
        )
        conn.commit()

        user_id = cursor.lastrowid
        print(f"Inserted user:")
        print(f"  ID         : {user_id}")
        print(f"  Name       : {name}")
        print(f"  Email      : {email}")
        print(f"  Password   : password123  (stored as hash)")
        print(f"  Created at : {created_at}")
        break
finally:
    conn.close()
