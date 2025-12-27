import socket
from game.net import send_json, recv_json
HOST = '127.0.0.1'
PORT = 5000
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5.0)
try:
    s.connect((HOST, PORT))
    send_json(s, {"role": "O"})
    # Wait for welcome
    msg = recv_json(s, timeout=5.0)
    print('RECEIVED:', msg)
except Exception as e:
    print('ERROR:', e)
finally:
    s.close()
