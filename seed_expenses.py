import sys
import random
from datetime import date, timedelta

sys.path.insert(0, ".")
from database.db import get_db

USER_ID = 2
COUNT = 50
MONTHS = 6

# --- Step 2: verify user exists ---
conn = get_db()
user = conn.execute("SELECT id FROM users WHERE id = ?", (USER_ID,)).fetchone()
conn.close()

if not user:
    print(f"No user found with id {USER_ID}.")
    sys.exit(1)

# --- Step 3: generate expenses ---

CATEGORY_WEIGHTS = [
    ("Food",          30),
    ("Transport",     20),
    ("Shopping",      15),
    ("Bills",         12),
    ("Other",         10),
    ("Health",         7),
    ("Entertainment",  6),
]

AMOUNT_RANGES = {
    "Food":          (50,   800),
    "Transport":     (20,   500),
    "Bills":         (200, 3000),
    "Health":        (100, 2000),
    "Entertainment": (100, 1500),
    "Shopping":      (200, 5000),
    "Other":         (50,  1000),
}

DESCRIPTIONS = {
    "Food": [
        "Lunch at Darshini", "Chai and snacks", "Swiggy order - biryani",
        "Zomato delivery", "Groceries from D-Mart", "Dinner at Saravana Bhavan",
        "Breakfast idli-vada", "Office canteen lunch", "Fruit and vegetables",
        "Monthly grocery run", "Pizza from Domino's", "Thali at local dhaba",
    ],
    "Transport": [
        "Ola cab to office", "Rapido bike ride", "Metro card recharge",
        "Auto to railway station", "Uber airport drop", "BMTC bus pass",
        "Petrol fill-up", "Parking charges", "Namma Metro top-up",
        "Rapido to market", "Cab to hospital",
    ],
    "Bills": [
        "Electricity bill - BESCOM", "Airtel broadband", "Jio postpaid bill",
        "DTH recharge - Tata Play", "Piped gas bill", "Water bill",
        "Society maintenance", "BSNL landline", "Netflix subscription",
        "Amazon Prime renewal", "Google One storage",
    ],
    "Health": [
        "Apollo pharmacy", "Medplus medicines", "Doctor consultation fee",
        "Lab tests - thyroid panel", "Gym membership", "Spectacles at Vision Express",
        "Dental check-up", "Practo teleconsult", "Vitamin supplements",
        "Physiotherapy session",
    ],
    "Entertainment": [
        "PVR movie ticket", "INOX weekend show", "BookMyShow booking",
        "Spotify premium", "PlayStation game", "Amusement park entry",
        "Escape room activity", "Comedy show tickets", "OTT subscription",
    ],
    "Shopping": [
        "Myntra kurta order", "Ajio ethnic wear", "Amazon - home essentials",
        "Flipkart electronics sale", "Lifestyle store", "H&M T-shirts",
        "FabIndia ethnic set", "Nike running shoes", "Decathlon sports gear",
        "Ikea home decor", "Reliance Trends clothing",
    ],
    "Other": [
        "Stationery from Crossword", "Gift for colleague", "Temple donation",
        "Charity - CRY", "Barber and salon", "Laundry service",
        "Courier charges", "Newspaper subscription", "Miscellaneous",
        "Mobile repair", "Key duplicate",
    ],
}

categories = [cat for cat, w in CATEGORY_WEIGHTS for _ in range(w)]

today = date.today()
start_date = today - timedelta(days=MONTHS * 30)

expenses = []
for _ in range(COUNT):
    category = random.choice(categories)
    lo, hi = AMOUNT_RANGES[category]
    amount = round(random.uniform(lo, hi), 2)
    description = random.choice(DESCRIPTIONS[category])
    days_range = (today - start_date).days
    expense_date = start_date + timedelta(days=random.randint(0, days_range))
    expenses.append((USER_ID, amount, category, expense_date.isoformat(), description))

expenses.sort(key=lambda r: r[3])

# --- Insert in single transaction ---
conn = get_db()
try:
    conn.execute("BEGIN")
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.execute("COMMIT")
except Exception as e:
    conn.execute("ROLLBACK")
    print(f"Insert failed, rolled back: {e}")
    sys.exit(1)
finally:
    conn.close()

# --- Step 4: confirm ---
dates = [r[3] for r in expenses]
print(f"Inserted  : {len(expenses)} expenses")
print(f"Date range: {min(dates)}  to  {max(dates)}")
print()
print("Sample (5 records):")
print(f"{'Date':<12} {'Category':<15} {'Amount (₹)':>10}  Description")
print("-" * 65)
for r in random.sample(expenses, 5):
    _, amount, category, exp_date, description = r
    print(f"{exp_date:<12} {category:<15} {amount:>10.2f}  {description}")
