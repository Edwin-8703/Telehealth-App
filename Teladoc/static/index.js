
const template = Handlebars.compile(
  '<div class="card message-content" style="width: 100%; padding: 10px; margin-top: 5px;"><h5>{{ user0 }}</h5><p>{{ content }}</p><div class="right">{{ date }} at {{ time }}</div></div>'
  );

const template0 = Handlebars.compile(
  '<div class="alert alert-dark" style="text-align: center; margin-top: 5px;">{{ user0 }} has left the Chat Room</div>'
);

const template1 = Handlebars.compile(
  '<div class="alert alert-success" style="text-align: center; margin-top: 5px;">{{ user0 }} has Joined the Chat Room</div>'
);

document.addEventListener('DOMContentLoaded', () => {

  var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

  socket.on('connect', () => { /* function to trigger when the socket connects */

    socket.emit('joined');

    document.querySelector('.slider').scrollTop = document.querySelector(".slider").scrollHeight;

    function sendMsg() {
      const text = document.querySelector('.typearea').value;
      const user0 = localStorage.getItem('username');
      var today = new Date();
      var date = today.getFullYear() + '-' + (today.getMonth() + 1) + '-' + today.getDate();
      var time = today.getHours() + ":" + today.getMinutes() + ":" + today.getSeconds();
      const word = template({'content': text, 'user0': user0, 'date': date, 'time': time});
      document.querySelector('#form1').reset();
      socket.emit('msg received', {'content': text, 'user0': user0, 'date': date, 'time': time, 'word': word});
    }

    document.querySelector('#message').addEventListener('keyup', (event) => {
      if (event.code == 'Enter') {
        sendMsg();
      }
    })

    document.querySelector('.send').addEventListener("click", () => {
      sendMsg();
    });

    document.querySelector('#home').onclick = () => {
      localStorage.removeItem('current_room');
      const user0 = localStorage.getItem('username');
      const left = template0({'user0': user0});
      document.querySelector('.slider').scrollTop = document.querySelector('.slider').scrollHeight;
      socket.emit('left', left);
    }

    document.querySelector('#logout').onclick = () => {
      localStorage.removeItem('current_room');
      localStorage.removeItem('username');
    }
  });

  socket.on('joined room', data => {

    if (!localStorage.getItem('username'))
      localStorage.setItem('username', data['user']);
    const enter = template1({'user0': localStorage.getItem('username')});
    localStorage.setItem('current_room', data['room']);
    document.querySelector('#msg-box').innerHTML += enter;
    document.querySelector('.slider').scrollTop = document.querySelector('.slider').scrollHeight;
  });

  socket.on('msg display', data => {

    const mesg = data['msg'];
    document.querySelector('#msg-box').innerHTML += mesg;
    document.querySelector('.slider').scrollTop = document.querySelector('.slider').scrollHeight;
  });

  socket.on('left room', data => {

    const left = data;
    document.querySelector('#msg-box').innerHTML += left;
    document.querySelector('.slider').scrollTop = document.querySelector('.slider').scrollHeight;
  });
});
