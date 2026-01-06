from flask import Blueprint, request, jsonify, current_app
from app.utils.network_utils import get_local_ip, listen_for_acknowledgment, send_acknowledgment, broadcast_receiver, listen_for_receiver, listen_for_handshake, send_handshake, BroadcastState
import threading
from app.extensions import app_state
from app.services.key_service import load_rsa_public_key, load_signature_public_key

handshake_bp = Blueprint("handshake", __name__)

@handshake_bp.route("/sender/discover", methods=["POST"])
def discover_receiver():
    print(app_state.role , "is the current role")
    if app_state.role != "SENDER":
        return jsonify({"error": "Not in sender mode"}), 403

    ip, port, name = listen_for_receiver()

    if not ip:
        return jsonify({"error": "No receiver found"}), 404
    print(f"Discovered receiver at {ip}:{port} with name {name}")
    app_state.receiver_ip = ip
    app_state.receiver_port = port
    app_state.receiver_name = name

    return jsonify({
        "message": "Receiver discovered",
        "receiver_ip": ip,
        "receiver_port": port,
        "receiver_name": name,
    })

@handshake_bp.route("/receiver/start", methods=["POST"])
def start_receiver():
    if app_state.role != "RECEIVER":
        return jsonify({"error": "Not in receiver mode"}), 403

    data = request.get_json() or {}
    name = data.get("name", "Receiver")
    ip = get_local_ip()
    port = 5050

    # Create shared state
    broadcast_state = BroadcastState()
    app_state.broadcast_state = broadcast_state

    # Thread 1: Broadcast availability
    broadcast_thread = threading.Thread(
        target=broadcast_receiver,
        args=(ip, port, name, broadcast_state),
        daemon=True
    )
    broadcast_thread.start()

    # Thread 2: Listen for handshake
    handshake_thread = threading.Thread(
        target=listen_for_handshake,
        args=(port, broadcast_state),
        daemon=True
    )
    handshake_thread.start()

    app_state.broadcast_thread = broadcast_thread
    app_state.handshake_thread = handshake_thread

    return jsonify({
        "message": "Receiver started: broadcasting and waiting for handshake",
        "name": name,
        "ip": ip,
        "port": port
    })


@handshake_bp.route("/receiver/status", methods=["GET"])
def receiver_status():
    """Poll this endpoint to check if handshake is received"""
    if app_state.role != "RECEIVER":
        return jsonify({"error": "Not in receiver mode"}), 403

    if not hasattr(app_state, 'broadcast_state'):
        return jsonify({"status": "NOT_STARTED"})

    state = app_state.broadcast_state

    if state.handshake_received:
        # 🔑 Store sender's public keys from handshake
        if 'rsa_public_key' in state.sender_info:
            app_state.peer_rsa_public_key = bytes.fromhex(state.sender_info['rsa_public_key'])
        if 'signature_public_key' in state.sender_info:
            app_state.peer_signature_public_key = bytes.fromhex(state.sender_info['signature_public_key'])
        
        return jsonify({
            "status": "READY",
            "sender_ip": state.sender_info["ip"],
            "sender_port": state.sender_info["port"],
            "sender_name": state.sender_info["name"]
        })
    else:
        return jsonify({"status": "WAITING"})

    
@handshake_bp.route("/receiver/acknowledge", methods=["POST"])
def receiver_acknowledge():
    if app_state.role != "RECEIVER":
        return jsonify({"error": "Not in receiver mode"}), 403

    data = request.get_json() or {}
    sender_ip = data.get("sender_ip")
    sender_port = data.get("sender_port")
    receiver_name = data.get("receiver_name", "Receiver")

    if not sender_ip or not sender_port:
        return jsonify({"error": "Sender IP and port required"}), 400

    receiver_ip = get_local_ip()
    receiver_port = 5050

    # 🔑 Load receiver's public keys
    receiver_rsa_public_key = load_rsa_public_key()
    receiver_signature_public_key = load_signature_public_key()

    # Send acknowledgment to sender with public keys
    success = send_acknowledgment(
        sender_ip, 
        sender_port, 
        receiver_ip, 
        receiver_port, 
        receiver_name,
    )

    if success:
        return jsonify({
            "message": "Acknowledgment sent",
            "receiver_ip": receiver_ip,
            "receiver_port": receiver_port
        })
    else:
        return jsonify({"error": "Failed to send acknowledgment"}), 500
    
@handshake_bp.route("/sender/handshake", methods=["POST"])
def sender_handshake():
    if app_state.role != "SENDER":
        return jsonify({"error": "Not in sender mode"}), 403

    data = request.get_json() or {}
    receiver_ip = data.get("receiver_ip")
    receiver_port = data.get("receiver_port", 5050)
    sender_name = data.get("sender_name", "Sender")

    if not receiver_ip:
        return jsonify({"error": "Receiver IP required"}), 400

    sender_ip = get_local_ip()
    sender_port = 5051

    # 🔑 Load sender's public keys
    sender_rsa_public_key = load_rsa_public_key()
    sender_signature_public_key = load_signature_public_key()

    # Send handshake with public keys
    success = send_handshake(
        receiver_ip, 
        receiver_port, 
        sender_ip, 
        sender_port, 
        sender_name
    )

    if success:
        # Start listening for acknowledgment
        ack_state = BroadcastState()
        app_state.ack_state = ack_state
        
        ack_thread = threading.Thread(
            target=listen_for_acknowledgment,
            args=(sender_port, ack_state),
            daemon=True
        )
        ack_thread.start()
        app_state.ack_thread = ack_thread

        return jsonify({
            "message": "Handshake sent, waiting for acknowledgment",
            "sender_ip": sender_ip,
            "sender_port": sender_port
        })
    else:
        return jsonify({"error": "Failed to send handshake"}), 500


@handshake_bp.route("/sender/ack_status", methods=["GET"])
def sender_ack_status():
    """Poll this endpoint to check if acknowledgment is received"""
    if app_state.role != "SENDER":
        return jsonify({"error": "Not in sender mode"}), 403

    if not hasattr(app_state, 'ack_state'):
        return jsonify({"status": "NOT_STARTED"})

    state = app_state.ack_state

    if state.ack_received:
        # 🔑 Store receiver's public keys from acknowledgment
        if hasattr(state, 'receiver_info'):
            if 'rsa_public_key' in state.receiver_info:
                app_state.peer_rsa_public_key = bytes.fromhex(state.receiver_info['rsa_public_key'])
            if 'signature_public_key' in state.receiver_info:
                app_state.peer_signature_public_key = bytes.fromhex(state.receiver_info['signature_public_key'])
        
        return jsonify({"status": "ACKNOWLEDGED"})
    else:
        return jsonify({"status": "WAITING"})