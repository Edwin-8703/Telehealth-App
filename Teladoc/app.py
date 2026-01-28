import os
import csv
import datetime
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from collections import deque
from . import diseaseprediction


app = Flask(__name__)
app.secret_key = 'mysecretkey'
socketio = SocketIO(app)

# PostgreSQL Configuration for Render
DB_URL = "postgresql://telehealth_3kbc_user:1MjH2GlKK4HFI4OlXkEd6mx5yZSdKxFj@dpg-d5ougn0gjchc73amq4mg-a.oregon-postgres.render.com/telehealth_3kbc"

def get_db_connection():
    # sslmode='require' is mandatory for Render connections
    conn = psycopg2.connect(DB_URL, sslmode='require')
    return conn

# SocketIO Global variables
_users_in_room = {} 
_room_of_sid = {} 
_name_of_sid = {} 

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('TelLandingPage.html')

@app.route('/About')
def About():
    return render_template('About.html')

@app.route('/consult')
def Consult():
    return render_template('Consult_home.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')
# Login page
@app.route('/login', methods=['GET', 'POST'])
def User():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            # We convert the database row to a standard dictionary for the session
            session['user'] = dict(user)
            return redirect('/user')
        else:
            return "Invalid username or password", 401
    else:
        return render_template('telehealthLoginPage.html')

# User registration page
@app.route('/register', methods=['GET', 'POST'])
def reg():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', (username, email, password))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/login')
    else:
        return render_template('telehealthRegisterPage.html')

# User profile page
@app.route('/user')
def user():
    if 'user' in session:
        user_data = session['user']
        return render_template('user.html', user=user_data)
    else:
        return redirect('/login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# User booking page
@app.route('/book', methods=['GET', 'POST'])
def Book():
    if request.method == 'POST':
        username = request.form['name']
        telephone = request.form['number']
        email = request.form['email']
        date = request.form['date']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO booking (name, telephone, email, date) VALUES (%s, %s, %s, %s)', (username, telephone, email, date))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/user')
    else:
        return render_template('BookAppointment.html')

@app.route('/message', methods=['GET', 'POST'])
def message():
    if request.method == 'POST':
        username = request.form['username']
        telephone = request.form['telephone']
        recipient = request.form['recipient']
        msg_content = request.form['message']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO messages (username, telephone, recipient, message, timestamp) VALUES (%s, %s, %s, %s, %s)", 
                    (username, telephone, recipient, msg_content, datetime.datetime.now()))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/user')
    else:
        return render_template('message.html')

# --- DISEASE PREDICTION ---

with open('templates/Testing.csv', newline='') as f:
    reader = csv.reader(f)
    symptoms = next(reader)
    symptoms = symptoms[:len(symptoms)-1]

@app.route('/phome', methods=['GET'])
def dropdown():
    return render_template('phome.html', symptoms=symptoms)

@app.route('/disease_predict', methods=['POST'])
def disease_predict():
    selected_symptoms = []
    for i in range(1, 6):
        symptom = request.form.get(f'Symptom{i}')
        if symptom and symptom not in selected_symptoms:
            selected_symptoms.append(symptom)

    disease = diseaseprediction.dosomething(selected_symptoms)
    return render_template('disease_predict.html', disease=disease, symptoms=symptoms)

# --- VIDEO CHAT / SOCKETIO ---

@app.route("/home", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        room_id = request.form['room_id']
        return redirect(url_for("entry_checkpoint", room_id=room_id))
    return render_template("home.html")

@app.route("/room/<string:room_id>/")
def enter_room(room_id):
    if room_id not in session:
        return redirect(url_for("entry_checkpoint", room_id=room_id))
    return render_template("chatroom.html", room_id=room_id, display_name=session[room_id]["name"], mute_audio=session[room_id]["mute_audio"], mute_video=session[room_id]["mute_video"])

@app.route("/room/<string:room_id>/checkpoint/", methods=["GET", "POST"])
def entry_checkpoint(room_id):
    if request.method == "POST":
        display_name = request.form['display_name']
        mute_audio = request.form['mute_audio']
        mute_video = request.form['mute_video']
        session[room_id] = {"name": display_name, "mute_audio": mute_audio, "mute_video": mute_video}
        return redirect(url_for("enter_room", room_id=room_id))
    return render_template("chatroom_checkpoint.html", room_id=room_id)

@socketio.on("connect")
def on_connect():
    print("New socket connected ", request.sid)

@socketio.on("join-room")
def on_join_room(data):
    sid = request.sid
    room_id = data["room_id"]
    display_name = session[room_id]["name"]
    
    join_room(room_id)
    _room_of_sid[sid] = room_id
    _name_of_sid[sid] = display_name
    
    emit("user-connect", {"sid": sid, "name": display_name}, broadcast=True, include_self=False, room=room_id)
    
    if room_id not in _users_in_room:
        _users_in_room[room_id] = [sid]
        emit("user-list", {"my_id": sid})
    else:
        usrlist = {u_id: _name_of_sid[u_id] for u_id in _users_in_room[room_id]}
        emit("user-list", {"list": usrlist, "my_id": sid})
        _users_in_room[room_id].append(sid)

@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    if sid in _room_of_sid:
        room_id = _room_of_sid[sid]
        display_name = _name_of_sid[sid]

        emit("user-disconnect", {"sid": sid}, broadcast=True, include_self=False, room=room_id)

        if room_id in _users_in_room:
            _users_in_room[room_id].remove(sid)
            if len(_users_in_room[room_id]) == 0:
                _users_in_room.pop(room_id)

        _room_of_sid.pop(sid)
        _name_of_sid.pop(sid)

@socketio.on("data")
def on_data(data):
    target_sid = data['target_id']
    socketio.emit('data', data, room=target_sid)

if __name__ == '__main__':
    socketio.run(app, debug=True)