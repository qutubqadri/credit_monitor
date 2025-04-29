from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
from datetime import datetime, date, timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'replace-this-with-secure-random')

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id_, username, password_hash):
        self.id = id_
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, username, password_hash FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(id_=row[0], username=row[1], password_hash=row[2])
    return None

# --- Database Initialization & Auto-Seeding ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    ''')
    # Cards table
    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            limit_amount REAL,
            due_date TEXT,
            apr REAL,
            current_balance REAL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    # Transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Auto-seed dummy data for new users only
    # (no cards for any user_id yet)
    conn.commit()
    conn.close()

init_db()

# --- Authentication Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        pw_hash = generate_password_hash(password)
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                      (username, pw_hash))
            conn.commit()
            user_id = c.lastrowid
        except sqlite3.IntegrityError:
            flash('Username already taken', 'danger')
            conn.close()
            return redirect(url_for('register'))
        conn.close()
        user = User(id_=user_id, username=username, password_hash=pw_hash)
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
        row = c.fetchone()
        conn.close()
        if row and check_password_hash(row[2], password):
            user = User(id_=row[0], username=row[1], password_hash=row[2])
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Helper to connect DB with user context ---
def get_db_cursor():
    conn = sqlite3.connect('database.db')
    return conn, conn.cursor()

# --- Protected App Routes ---
@app.route('/')
def index():
    # Render the spinner page; its meta-refresh will go to /dashboard
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn, c = get_db_cursor()
    # Fetch user's cards
    c.execute('SELECT * FROM cards WHERE user_id = ?', (current_user.id,))
    cards = c.fetchall()
    # Income/expenses
    c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type='income'", (current_user.id,))
    income = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type='expense'", (current_user.id,))
    expenses = c.fetchone()[0] or 0
    conn.close()
    return render_template('dashboard.html', cards=cards, income=income, expenses=expenses)

@app.route('/add_card', methods=['GET', 'POST'])
@login_required
def add_card():
    if request.method == 'POST':
        name = request.form['name']
        limit_amount = float(request.form['limit'])
        due_date = request.form['due_date']
        apr = float(request.form['apr'])
        conn, c = get_db_cursor()
        c.execute('INSERT INTO cards (user_id, name, limit_amount, due_date, apr) VALUES (?, ?, ?, ?, ?)',
                  (current_user.id, name, limit_amount, due_date, apr))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('add_card.html')

@app.route('/update_balance/<int:card_id>', methods=['POST'])
@login_required
def update_balance(card_id):
    new_balance = float(request.form['new_balance'])
    conn, c = get_db_cursor()
    c.execute('UPDATE cards SET current_balance = ? WHERE id = ? AND user_id = ?',
              (new_balance, card_id, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        type_ = request.form['type']
        amount = float(request.form['amount'])
        conn, c = get_db_cursor()
        c.execute('INSERT INTO transactions (user_id, type, amount) VALUES (?, ?, ?)',
                  (current_user.id, type_, amount))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('add_expense.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

@app.route('/edit_card/<int:card_id>', methods=['GET', 'POST'])
@login_required
def edit_card(card_id):
    conn, c = get_db_cursor()
    # Fetch the card, ensure it belongs to this user
    c.execute('SELECT id, name, limit_amount, due_date, apr FROM cards '
              'WHERE id = ? AND user_id = ?', (card_id, current_user.id))
    card = c.fetchone()
    if not card:
        conn.close()
        flash('Card not found.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name        = request.form['name']
        limit_amt   = float(request.form['limit'])
        due_date    = request.form['due_date']
        apr         = float(request.form['apr'])
        c.execute('''
            UPDATE cards
            SET name = ?, limit_amount = ?, due_date = ?, apr = ?
            WHERE id = ? AND user_id = ?
        ''', (name, limit_amt, due_date, apr, card_id, current_user.id))
        conn.commit()
        conn.close()
        flash('Card updated successfully.', 'success')
        return redirect(url_for('dashboard'))

    conn.close()
    # Render the same form as add_card.html but pre-populated
    return render_template('edit_card.html', card=card)

@app.route('/delete_card/<int:card_id>', methods=['POST'])
@login_required
def delete_card(card_id):
    conn, c = get_db_cursor()
    c.execute('DELETE FROM cards WHERE id = ? AND user_id = ?', (card_id, current_user.id))
    conn.commit()
    conn.close()
    flash('Card deleted.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_transaction/<int:tx_id>', methods=['POST'])
@login_required
def delete_transaction(tx_id):
    conn, c = get_db_cursor()
    c.execute('DELETE FROM transactions WHERE id = ? AND user_id = ?', (tx_id, current_user.id))
    conn.commit()
    conn.close()
    flash('Transaction removed.', 'success')
    return redirect(url_for('dashboard'))

