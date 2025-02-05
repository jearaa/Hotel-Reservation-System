from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = 'secretkey'

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password123",
    database="hotel_db"
)
cursor = db.cursor()

# Initialize database tables
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) UNIQUE,
        password VARCHAR(255),
        confirm_password VARCHAR(255),
        is_admin BOOLEAN DEFAULT FALSE
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INT AUTO_INCREMENT PRIMARY KEY,
        room_number VARCHAR(50) UNIQUE,
        room_type VARCHAR(255),
        status ENUM('available', 'reserved') DEFAULT 'available'
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        room_id INT,
        date DATE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (room_id) REFERENCES rooms(id)
    )
""")
db.commit()

# Admin default credentials
cursor.execute("SELECT * FROM users WHERE username='admin'")
if not cursor.fetchone():
    cursor.execute("INSERT INTO users (username, password, confirm_password, is_admin) VALUES (%s, %s, %s, %s)",
                   ('admin', 'adminpogi', 'adminpogi', True))
    db.commit()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password == confirm_password:
            try:
                cursor.execute("INSERT INTO users (username, password, confirm_password) VALUES (%s, %s, %s)",
                               (username, password, confirm_password))
                db.commit()
                return redirect('/login')
            except:
                return "Username already exists."
        else:
            return "Passwords do not match."
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            session['is_admin'] = user[4]
            if session['is_admin']:
                return redirect('/admin_dashboard')
            else:
                return redirect('/user_dashboard')
        return "Invalid credentials."
    return render_template('login.html')

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('is_admin', False):
        return redirect('/login')
    cursor.execute("SELECT * FROM rooms WHERE status='available'")
    rooms = cursor.fetchall()
    cursor.execute("SELECT reservations.id, rooms.room_number, reservations.date FROM reservations INNER JOIN rooms ON reservations.room_id = rooms.id WHERE reservations.user_id=%s", (session['user_id'],))
    reservations = cursor.fetchall()
    return render_template('user_dashboard.html', rooms=rooms, reservations=reservations)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin', False):
        return redirect('/login')
    cursor.execute("SELECT * FROM rooms")
    rooms = cursor.fetchall()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    return render_template('admin_dashboard.html', rooms=rooms, users=users)

@app.route('/add_room', methods=['POST'])
def add_room():
    if 'user_id' in session and session.get('is_admin', False):
        room_number = request.form['room_number']
        room_type = request.form['room_type']
        try:
            cursor.execute("INSERT INTO rooms (room_number, room_type) VALUES (%s, %s)", (room_number, room_type))
            db.commit()
        except:
            return "Room number already exists."
    return redirect('/admin_dashboard')


@app.route('/book/<int:room_id>', methods=['POST'])
def book(room_id):
    if 'user_id' not in session:
        return redirect('/login')
    date = request.form['date']
    cursor.execute("UPDATE rooms SET status='reserved' WHERE id=%s", (room_id,))
    cursor.execute("INSERT INTO reservations (user_id, room_id, date) VALUES (%s, %s, %s)", (session['user_id'], room_id, date))
    db.commit()
    return redirect('/user_dashboard')

@app.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
def cancel_reservation(reservation_id):
    if 'user_id' not in session:
        return redirect('/login')
    cursor.execute("SELECT room_id FROM reservations WHERE id=%s", (reservation_id,))
    room_id = cursor.fetchone()
    if room_id:
        cursor.execute("UPDATE rooms SET status='available' WHERE id=%s", (room_id[0],))
        cursor.execute("DELETE FROM reservations WHERE id=%s", (reservation_id,))
        db.commit()
    return redirect('/user_dashboard')

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' in session and session.get('is_admin', False):
        cursor.execute("SELECT room_id FROM reservations WHERE user_id=%s", (user_id,))
        rooms = cursor.fetchall()
        for room in rooms:
            cursor.execute("UPDATE rooms SET status='available' WHERE id=%s", (room[0],))
        cursor.execute("DELETE FROM reservations WHERE user_id=%s", (user_id,))
        cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        db.commit()
    return redirect('/admin_dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
