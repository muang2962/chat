from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, emit
import sqlite3

app = Flask(__name__)
app.secret_key = "muelchatservice"
socketio = SocketIO(app)

def connect_db():
    return sqlite3.connect("chat.db", check_same_thread=False)

def get_db_connection():
    conn = sqlite3.connect('chat.db')
    conn.row_factory = sqlite3.Row 
    return conn

def save_message(room, name, message):
    conn = get_db_connection()
    conn.execute("INSERT INTO messages (room, name, message) VALUES (?, ?, ?)", 
                 (room, name, message))
    conn.commit()
    conn.close()

def get_messages(room):
    conn = get_db_connection()
    messages = conn.execute("SELECT name, message, timestamp FROM messages WHERE room = ? ORDER BY timestamp ASC", 
                            (room,)).fetchall()
    conn.close()
    return messages


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "@muel2962" and password == "!CHmuel0602!":
            session["logged_in"] = True
            return redirect(url_for("admin"))
        else:
            return "Invalid credentials", 401

    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    if not session.get("logged_in"):
        return redirect(url_for("admin_login"))

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM rooms")
    rooms = cur.fetchall()

    cur.execute("SELECT * FROM messages ORDER BY timestamp DESC")
    messages = cur.fetchall()
    conn.close()

    return render_template("admin.html", rooms=rooms, messages=messages)


@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "POST":
        name = request.form["name"]
        room = request.form["room"]

        conn = connect_db()
        cur = conn.cursor()

        cur.execute("INSERT OR IGNORE INTO rooms (room, users) VALUES (?, ?)", (room, name))
        conn.commit()
        conn.close()

        return render_template("chat.html", name=name, room=room)

    return render_template("main.html")

@app.route("/chat", methods=["POST"])
def chat():
    name = request.form["name"]
    room = request.form["room"]

    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO rooms (room, users) VALUES (?, ?)", (room, name))
    conn.commit()
    conn.close()

    return render_template("chat.html", name=name, room=room)

def create_tables():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room TEXT NOT NULL,
        name TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room TEXT UNIQUE NOT NULL,
        users TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

create_tables()

@socketio.on("message")
def handle_message(data):
    room = data["room"]
    name = data["name"]
    message = data["message"]

    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO messages (room, name, message) VALUES (?, ?, ?)", (room, name, message))
    conn.commit()
    conn.close()

    socketio.emit("message", {"name": name, "message": message}, room=room)


@socketio.on("join")
def handle_join(data):
    name = data["name"]
    room = data["room"]
    
    socketio.emit("joined", f"{name}님이 입장했습니다.", room=room)

    join_room(room)


@socketio.on("leave")
def handle_leave(data):
    name = data["name"]
    room = data["room"]
    
    emit("message", {"name": "System", "message": f"{name}님이 나갔습니다."}, room=room)
    leave_room(room)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", debug=True)
