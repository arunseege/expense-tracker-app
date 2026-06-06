import sys, random
sys.path.insert(0, ".")
from database.db import get_db

conn = get_db()
rows = conn.execute(
    "SELECT date, category, amount, description FROM expenses WHERE user_id = ? ORDER BY date",
    (2,)
).fetchall()
conn.close()

dates = [r[0] for r in rows]
print(f"Inserted  : {len(rows)} expenses")
print(f"Date range: {min(dates)}  to  {max(dates)}")
print()
print(f"{'Date':<12} {'Category':<15} {'Amount':>10}  Description")
print("-" * 66)
for r in random.sample(rows, 5):
    print(f"{r[0]:<12} {r[1]:<15} {r[2]:>10.2f}  {r[3]}")
