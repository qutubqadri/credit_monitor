# seed_data.py

import sqlite3
from datetime import date, timedelta

def seed():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # --- Seed dummy credit cards ---
    dummy_cards = [
        # name,      limit,    due_date,        apr,    current_balance
        ("Visa Platinum",  5000.00, (date.today() + timedelta(days=10)).isoformat(), 18.99, 1234.56),
        ("Mastercard Gold",10000.00,(date.today() + timedelta(days=20)).isoformat(), 22.49,  789.01),
        ("Amex Green",      3000.00, (date.today() + timedelta(days=5)).isoformat(),  15.99,  345.67),
    ]
    for name, limit_amt, due, apr, bal in dummy_cards:
        c.execute('''
            INSERT INTO cards (name, limit_amount, due_date, apr, current_balance)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, limit_amt, due, apr, bal))

    # --- Seed dummy income/expenses ---
    dummy_tx = [
        ("income",  5000.00),
        ("expense", 1200.50),
        ("expense",  345.75),
        ("expense",  678.90),
        ("income",  2500.00),
    ]
    for ttype, amt in dummy_tx:
        c.execute('INSERT INTO transactions (type, amount) VALUES (?, ?)', (ttype, amt))

    conn.commit()
    conn.close()
    print("✅ Seeded database with dummy cards and transactions.")

if __name__ == "__main__":
    seed()
