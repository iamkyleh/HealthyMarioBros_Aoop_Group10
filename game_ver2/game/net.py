import json
import struct
import socket
import errno

def send_json(sock, obj):
    """Send JSON data with length header. Non-blocking, handles partial sends."""
    try:
        data = json.dumps(obj).encode('utf-8')
        header = struct.pack('!I', len(data))
        sock.sendall(header + data)
    except (socket.error, OSError, ConnectionError, BrokenPipeError) as e:
        # Re-raise connection errors so caller can handle them
        raise
    except Exception as e:
        # Wrap other exceptions
        raise ConnectionError(f"Failed to send data: {e}") from e

def _recv_all(sock, n, timeout=0.01):
    """Receive exactly n bytes. Returns None if timeout or connection closed."""
    buf = bytearray()
    original_timeout = sock.gettimeout()
    try:
        # Only set timeout if it's different from current
        if sock.gettimeout() != timeout:
            sock.settimeout(timeout)
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                return None  # Connection closed
            buf.extend(chunk)
        return bytes(buf)
    except socket.timeout:
        return None  # Timeout - no data available
    except (socket.error, OSError) as e:
        err_code = getattr(e, 'winerror', getattr(e, 'errno', None))
        if err_code in (errno.EAGAIN, errno.EWOULDBLOCK):
            return None  # Non-blocking socket would block
        return None  # Connection error
    finally:
        # Restore original timeout
        if original_timeout != sock.gettimeout():
            try:
                sock.settimeout(original_timeout)
            except:
                pass

def recv_json(sock, timeout=0.01):
    """
    Receive JSON data. Returns None if no data available (non-blocking).
    timeout: how long to wait for data (0.01 = 10ms default)
    """
    try:
        header = _recv_all(sock, 4, timeout)
        if header is None:
            return None
        (length,) = struct.unpack('!I', header)
        data = _recv_all(sock, length, timeout)
        if data is None:
            return None
        return json.loads(data.decode('utf-8'))
    except (socket.error, OSError, json.JSONDecodeError):
        return None
