import socket
import json
import time
import threading
from app.services.key_service import load_signature_public_key, load_rsa_public_key
from cryptography.hazmat.primitives import serialization

DISCOVERY_PORT = 9999
BROADCAST_ADDR = "255.255.255.255"


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


# Shared state for stopping threads
class BroadcastState:
    def __init__(self):
        self.should_stop = False
        self.handshake_received = False
        self.sender_info = {}


def broadcast_receiver(ip, port, name, state, interval=3):
    """Broadcasts receiver availability until handshake is received"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    payload = {
        "type": "RECEIVER_AVAILABLE",
        "name": name,
        "ip": ip,
        "port": port
    }

    while not state.should_stop:
        sock.sendto(
            json.dumps(payload).encode(),
            (BROADCAST_ADDR, DISCOVERY_PORT)
        )
        time.sleep(interval)
    
    sock.close()


def listen_for_handshake(port, state, timeout=60):
    """Listens for sender's handshake on receiver's port"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    sock.settimeout(1)  # Short timeout for checking should_stop

    start_time = time.time()
    
    while not state.should_stop and (time.time() - start_time) < timeout:
        try:
            data, addr = sock.recvfrom(4096)
            message = json.loads(data.decode())

            if message.get("type") == "SENDER_HANDSHAKE":
                state.sender_info = {
                    "ip": message["ip"],
                    "port": message["port"],
                    "name": message["name"]
                }
                state.handshake_received = True
                state.should_stop = True  # Stop broadcasting
                break

        except socket.timeout:
            continue  # Keep looping
        except Exception as e:
            print(f"Error receiving handshake: {e}")
            continue
    
    sock.close()


def send_handshake(receiver_ip, receiver_port, sender_ip, sender_port, sender_name):
    """Sender sends handshake to receiver"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sign_public_key = load_signature_public_key()
    payload = {
        "type": "SENDER_HANDSHAKE",
        "name": sender_name,
        "ip": sender_ip,
        "port": sender_port,
        "public_key": sign_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    }
    print("Sending handshake payload:", payload)

    try:
        sock.sendto(
            json.dumps(payload).encode(),
            (receiver_ip, receiver_port)
        )
        return True
    except Exception as e:
        print(f"Handshake failed: {e}")
        return False
    finally:
        sock.close()


def listen_for_receiver(timeout=10):
    """Sender listens for receiver broadcasts"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", DISCOVERY_PORT))
    sock.settimeout(timeout)

    try:
        data, _ = sock.recvfrom(4096)
        message = json.loads(data.decode())
        print("Message received:", message)
        if message.get("type") == "RECEIVER_AVAILABLE":
            return message["ip"], message["port"], message["name"]

    except socket.timeout:
        return None, None, None
    finally:
        sock.close()
    return None, None, None

def send_acknowledgment(sender_ip, sender_port, receiver_ip, receiver_port, receiver_name):
    """Receiver sends acknowledgment back to sender"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rsa_public_key = load_rsa_public_key()
    payload = {
        "type": "RECEIVER_ACK",
        "name": receiver_name,
        "ip": receiver_ip,
        "port": receiver_port,
        "signature_public_key": rsa_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    }

    try:
        sock.sendto(
            json.dumps(payload).encode(),
            (sender_ip, sender_port)
        )
        return True
    except Exception as e:
        print(f"Acknowledgment failed: {e}")
        return False
    finally:
        sock.close()

def listen_for_acknowledgment(port, state, timeout=30):
    """Sender listens for receiver's acknowledgment"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    sock.settimeout(1)

    start_time = time.time()
    
    while not state.should_stop and (time.time() - start_time) < timeout:
        try:
            data, addr = sock.recvfrom(4096)
            message = json.loads(data.decode())

            if message.get("type") == "RECEIVER_ACK":
                state.ack_received = True
                state.receiver_info = {
                    "ip": message["ip"],
                    "port": message["port"],
                    "name": message["name"]
                }
                state.should_stop = True
                break

        except socket.timeout:
            continue
        except Exception as e:
            print(f"Error receiving acknowledgment: {e}")
            continue
    
    sock.close()