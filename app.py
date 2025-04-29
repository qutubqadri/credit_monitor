from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

#initialize the database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Create tables if they don't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            limit_amount REAL,
            due_date TEXT,
            apr REAL,
            current_balance REAL DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            amount REAL,
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Check if we've already seeded
    c.execute('SELECT COUNT(*) FROM cards')
    if c.fetchone()[0] == 0:
        # --- Seed dummy credit cards ---
        from datetime import date, timedelta
        dummy_cards = [
            ("Visa Platinum",   5000.00, (date.today() + timedelta(days=10)).isoformat(), 18.99, 1234.56),
            ("Mastercard Gold", 10000.00,(date.today() + timedelta(days=20)).isoformat(), 22.49,  789.01),
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

init_db()

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM cards')
    cards = c.fetchall()
    
    c.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
    income = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
    expenses = c.fetchone()[0] or 0
    conn.close()

    return render_template('dashboard.html', cards=cards, income=income, expenses=expenses)

@app.route('/add_card', methods=['GET', 'POST'])
def add_card():
    if request.method == 'POST':
        name = request.form['name']
        limit_amount = float(request.form['limit'])
        due_date = request.form['due_date']
        apr = float(request.form['apr'])
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO cards (name, limit_amount, due_date, apr) VALUES (?, ?, ?, ?)',
                  (name, limit_amount, due_date, apr))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('add_card.html')

@app.route('/update_balance/<int:card_id>', methods=['POST'])
def update_balance(card_id):
    new_balance = float(request.form['new_balance'])
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE cards SET current_balance = ? WHERE id = ?', (new_balance, card_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        type_ = request.form['type']
        amount = float(request.form['amount'])
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO transactions (type, amount) VALUES (?, ?)', (type_, amount))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('add_expense.html')

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    # disable the reloader so Render’s health‐check sees the actual bound socket
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )

