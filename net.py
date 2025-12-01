# net.py
import json
import struct

# Send a JSON object with a 4-byte big-endian length header
def send_json(sock, obj):
    data = json.dumps(obj).encode('utf-8')
    header = struct.pack('!I', len(data))
    sock.sendall(header + data)

# Receive exactly n bytes
def _recv_all(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)

# Receive a length-prefixed JSON object
def recv_json(sock):
    header = _recv_all(sock, 4)
    if header is None:
        return None
    (length,) = struct.unpack('!I', header)
    data = _recv_all(sock, length)
    if data is None:
        return None
    return json.loads(data.decode('utf-8'))
