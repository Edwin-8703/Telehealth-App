
import os
import csv
import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from flask_socketio import SocketIO, emit, join_room, leave_room
from collections import deque
import diseaseprediction
import pymysql.cursors

app = Flask(__name__)
messages = []
app.secret_key = 'mysecretkey'

socketio = SocketIO(app)


_users_in_room = {} # stores room wise user list
_room_of_sid = {} # stores room joined by an used
_name_of_sid = {} # stores display name of users

# MySQL Configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'telehealth'
mysql = MySQL(app)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 # disable caching
# array storing the list of Chat Rooms
Crooms = []

# array storing the list of logged in users
users = []

roomMsgs = dict()

# appends the default chat room
Crooms.append("Main")

# Homepage
@app.route('/')
def home():
    return render_template('TelLandingPage.html')

# About us
@app.route('/About')
def About():
    return render_template('About.html')


#consult page
@app.route('/consult')
def Consult():
    return render_template('Consult_home.html')

# contact us
@app.route('/contact')
def contact():
    return render_template('contact.html')


# Login page
@app.route('/login', methods=['GET', 'POST'])
def User():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        if user:
            session['user'] = user
            return redirect('/user')

    else:
        return render_template('telehealthLoginPage.html')

# User registration page
@app.route('/register', methods=['GET', 'POST'])
def reg():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO users (username,email, password) VALUES (%s,%s, %s)', (username, email,password))
        mysql.connection.commit()
        cursor.close()
        return redirect('/login')
    else:
        return render_template('telehealthRegisterPage.html')

# User page
@app.route('/user')
def user():
    if 'user' in session:
        user = session['user']
        return render_template('user.html', user=user)
    else:
        return redirect('/login')

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('admin', None)
    return redirect('/login')


# User booking page
@app.route('/book', methods=['GET', 'POST'])
def Book():
    if request.method == 'POST':
        username = request.form['name']
        telephone = request.form['number']
        email = request.form['email']
        date = request.form['date']
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO booking (name,telephone,email, date) VALUES (%s,%s,%s, %s)', (username, telephone, email,date))
        mysql.connection.commit()
        cursor.close()
        return redirect('/user')
    else:
        return render_template('BookAppointment.html')



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
        session[room_id] = {"name": display_name, "mute_audio":mute_audio, "mute_video":mute_video}
        return redirect(url_for("enter_room", room_id=room_id))

    return render_template("chatroom_checkpoint.html", room_id=room_id)
    


@socketio.on("connect")
def on_connect():
    sid = request.sid
    print("New socket connected ", sid)
    

@socketio.on("join-room")
def on_join_room(data):
    sid = request.sid
    room_id = data["room_id"]
    display_name = session[room_id]["name"]
    
    # register sid to the room
    join_room(room_id)
    _room_of_sid[sid] = room_id
    _name_of_sid[sid] = display_name
    
    # broadcast to others in the room
    print("[{}] New member joined: {}<{}>".format(room_id, display_name, sid))
    emit("user-connect", {"sid": sid, "name": display_name}, broadcast=True, include_self=False, room=room_id)
    
    # add to user list maintained on server
    if room_id not in _users_in_room:
        _users_in_room[room_id] = [sid]
        emit("user-list", {"my_id": sid}) # send own id only
    else:
        usrlist = {u_id:_name_of_sid[u_id] for u_id in _users_in_room[room_id]}
        emit("user-list", {"list": usrlist, "my_id": sid}) # send list of existing users to the new member
        _users_in_room[room_id].append(sid) # add new member to user list maintained on server

    print("\nusers: ", _users_in_room, "\n")


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    room_id = _room_of_sid[sid]
    display_name = _name_of_sid[sid]

    print("[{}] Member left: {}<{}>".format(room_id, display_name, sid))
    emit("user-disconnect", {"sid": sid}, broadcast=True, include_self=False, room=room_id)

    _users_in_room[room_id].remove(sid)
    if len(_users_in_room[room_id]) == 0:
        _users_in_room.pop(room_id)

    _room_of_sid.pop(sid)
    _name_of_sid.pop(sid)

    print("\nusers: ", _users_in_room, "\n")


@socketio.on("data")
def on_data(data):
    sender_sid = data['sender_id']
    target_sid = data['target_id']
    if sender_sid != request.sid:
        print("[Not supposed to happen!] request.sid and sender_id don't match!!!")

    if data["type"] != "new-ice-candidate":
        print('{} message from {} to {}'.format(data["type"], sender_sid, target_sid))
    socketio.emit('data', data, room=target_sid)



@app.route('/message',  methods=['GET', 'POST'])
def message():
     if request.method == 'POST':
        # Get form data
        username = request.form['username']
        telephone = request.form['telephone']
        recipient = request.form['recipient']
        message = request.form['message']
        
        # Insert data into database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO messages (username, telephone, recipient, message, timestamp) VALUES (%s, %s, %s, %s, %s)", (username, telephone, recipient, message, datetime.datetime.now()))
        mysql.connection.commit()
        cur.close()
        
        # Redirect to user page
        return redirect('/user')

     else:
    
        # Render home page template
        return render_template('message.html')



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
    if(request.form['Symptom1']!="") and (request.form['Symptom1'] not in selected_symptoms):
        selected_symptoms.append(request.form['Symptom1'])
    if(request.form['Symptom2']!="") and (request.form['Symptom2'] not in selected_symptoms):
        selected_symptoms.append(request.form['Symptom2'])
    if(request.form['Symptom3']!="") and (request.form['Symptom3'] not in selected_symptoms):
        selected_symptoms.append(request.form['Symptom3'])
    if(request.form['Symptom4']!="") and (request.form['Symptom4'] not in selected_symptoms):
        selected_symptoms.append(request.form['Symptom4'])
    if(request.form['Symptom5']!="") and (request.form['Symptom5'] not in selected_symptoms):
        selected_symptoms.append(request.form['Symptom5'])

    disease = diseaseprediction.dosomething(selected_symptoms)
    return render_template('disease_predict.html',disease=disease,symptoms=symptoms)

if __name__ == '__main__':
   socketio.run(app, debug=True)
