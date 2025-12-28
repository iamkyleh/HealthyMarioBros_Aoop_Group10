import json
import struct
import socket
import errno
import select

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
    if n <= 0:
        return b''
    
    buf = bytearray()
    
    # Don't change socket timeout - use whatever is already set
    # The caller should set the timeout on the socket before calling
    try:
        # Read until we have all n bytes
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                # Connection closed
                return None
            buf.extend(chunk)
        
        return bytes(buf)
    except socket.timeout:
        # Timeout - no data available
        return None
    except (socket.error, OSError) as e:
        err_code = getattr(e, 'winerror', getattr(e, 'errno', None))
        if err_code in (errno.EAGAIN, errno.EWOULDBLOCK):
            return None
        # Other socket errors
        return None

def recv_json(sock, timeout=0.01):
    """
    Receive JSON data. Returns None if no data available (non-blocking).
    timeout: how long to wait for data (0.01 = 10ms default)
    Note: This function will temporarily set the socket timeout if needed.
    """
    original_timeout = sock.gettimeout()
    try:
        # Set socket timeout if needed (for the initial welcome message)
        if timeout is not None and timeout > 0:
            if original_timeout != timeout:
                sock.settimeout(timeout)
        
        # Try to read the header
        header = _recv_all(sock, 4, timeout)
        if header is None or len(header) != 4:
            return None
        
        (length,) = struct.unpack('!I', header)
        if length == 0 or length > 10 * 1024 * 1024:  # Sanity check: max 10MB
            return None
        
        # Read the data
        data = _recv_all(sock, length, timeout)
        if data is None or len(data) != length:
            return None
        
        # Parse JSON
        return json.loads(data.decode('utf-8'))
    except struct.error:
        return None
    except json.JSONDecodeError:
        return None
    except (socket.error, OSError):
        return None
    except Exception:
        return None
    finally:
        # Restore original timeout
        if original_timeout != sock.gettimeout():
            try:
                sock.settimeout(original_timeout)
            except:
                pass
