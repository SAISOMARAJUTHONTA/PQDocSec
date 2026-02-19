import threading
import base64
from flask import Blueprint, request, jsonify

from app.extensions import app_state
from app.services.pqc_key_service import (
    store_receiver_kyber_public_key,
    store_sender_dilithium_public_key
)
from app.utils.network_utils import (
    get_local_ip,
    listen_for_receiver,
    broadcast_receiver,
    listen_for_handshake,
    listen_for_acknowledgment,
    send_handshake,
    send_acknowledgment,
    BroadcastState
)

from app.services.pqc_key_service import (
    load_kyber_public_key,
    load_dilithium_public_key
)

# --------------------------------------------------
# Blueprint
# --------------------------------------------------

pqc_handshake_bp = Blueprint("pqc_handshake", __name__)

# ==================================================
# SENDER: Discover receiver
# ==================================================

@pqc_handshake_bp.route("/pqc/sender/discover", methods=["POST"])
def discover_receiver():

    if app_state.role != "SENDER":
        return jsonify({"error": "Not in sender mode"}), 403

    ip, port, name = listen_for_receiver()

    if not ip:
        return jsonify({"error": "No receiver found"}), 404

    app_state.receiver_ip = ip
    app_state.receiver_port = port
    app_state.receiver_name = name

    return jsonify({
        "message": "Receiver discovered",
        "receiver_ip": ip,
        "receiver_port": port,
        "receiver_name": name
    })


# ==================================================
# RECEIVER: Start broadcasting & listening
# ==================================================

@pqc_handshake_bp.route("/pqc/receiver/start", methods=["POST"])
def start_receiver():

    if app_state.role != "RECEIVER":
        return jsonify({"error": "Not in receiver mode"}), 403

    data = request.get_json() or {}
    receiver_name = data.get("name", "Receiver")

    receiver_ip = get_local_ip()
    receiver_port = 5051

    broadcast_state = BroadcastState()
    app_state.broadcast_state = broadcast_state

    # Broadcast availability
    threading.Thread(
        target=broadcast_receiver,
        args=(receiver_ip, receiver_port, receiver_name, broadcast_state),
        daemon=True
    ).start()

    # Listen for handshake
    threading.Thread(
        target=listen_for_handshake,
        args=(receiver_port, broadcast_state),
        daemon=True
    ).start()

    return jsonify({
        "message": "Receiver started (PQC)",
        "name": receiver_name,
        "ip": receiver_ip,
        "port": receiver_port
    })


# ==================================================
# RECEIVER: Poll handshake status
# ==================================================

@pqc_handshake_bp.route("/pqc/receiver/status", methods=["GET"])
def receiver_status():

    if app_state.role != "RECEIVER":
        return jsonify({"error": "Not in receiver mode"}), 403

    if not hasattr(app_state, "broadcast_state"):
        return jsonify({"status": "NOT_STARTED"})

    state = app_state.broadcast_state

    if not state.handshake_received:
        return jsonify({"status": "WAITING"})

    sender_info = state.sender_info

    # Store sender Dilithium public key
    app_state.peer_dilithium_public_key = bytes.fromhex(sender_info["dilithium_public_key"])
    store_sender_dilithium_public_key(
        bytes.fromhex(sender_info["dilithium_public_key"])
    )

    return jsonify({
        "status": "READY",
        "sender_ip": sender_info["ip"],
        "sender_port": sender_info["port"],
        "sender_name": sender_info["name"]
    })


# ==================================================
# RECEIVER → SENDER: Send acknowledgment (Kyber PK)
# ==================================================

@pqc_handshake_bp.route("/pqc/receiver/acknowledge", methods=["POST"])
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

    kyber_pk = load_kyber_public_key()

    payload = {
        "type": "RECEIVER_ACK",
        "name": receiver_name,
        "ip": receiver_ip,
        "port": receiver_port,
        "kyber_public_key": kyber_pk.hex()
    }



    success = send_acknowledgment(sender_ip, sender_port, receiver_ip, receiver_port, receiver_name)

    if not success:
        return jsonify({"error": "Failed to send acknowledgment"}), 500

    return jsonify({
        "message": "Acknowledgment sent (PQC)",
        "receiver_ip": receiver_ip,
        "receiver_port": receiver_port
    })


# ==================================================
# SENDER → RECEIVER: Send handshake (Dilithium PK)
# ==================================================

@pqc_handshake_bp.route("/pqc/sender/handshake", methods=["POST"])
def sender_handshake():

    if app_state.role != "SENDER":
        return jsonify({"error": "Not in sender mode"}), 403

    data = request.get_json() or {}
    receiver_ip = data.get("receiver_ip")
    receiver_port = data.get("receiver_port", 5050)
    sender_name = data.get("sender_name", "Sender")
    print(f"Received handshake request for receiver {receiver_ip}:{receiver_port}")
    if not receiver_ip:
        return jsonify({"error": "Receiver IP required"}), 400

    sender_ip = get_local_ip()
    sender_port = 5051

    dilithium_pk = load_dilithium_public_key()

    payload = {
        "type": "SENDER_HANDSHAKE",
        "name": sender_name,
        "ip": sender_ip,
        "port": sender_port,
        "dilithium_public_key": dilithium_pk.hex()
    }
    print("Prepared handshake payload:", payload)
    success = send_handshake(receiver_ip, receiver_port, sender_ip, sender_port, sender_name)

    if not success:
        return jsonify({"error": "Handshake failed"}), 500

    ack_state = BroadcastState()
    app_state.ack_state = ack_state

    threading.Thread(
        target=listen_for_acknowledgment,
        args=(sender_port, ack_state),
        daemon=True
    ).start()

    return jsonify({
        "message": "Handshake sent (PQC)",
        "sender_ip": sender_ip,
        "sender_port": sender_port
    })


# ==================================================
# SENDER: Poll acknowledgment status
# ==================================================

@pqc_handshake_bp.route("/pqc/sender/ack_status", methods=["GET"])
def sender_ack_status():

    if app_state.role != "SENDER":
        return jsonify({"error": "Not in sender mode"}), 403

    if not hasattr(app_state, "ack_state"):
        return jsonify({"status": "NOT_STARTED"})

    state = app_state.ack_state

    if not state.ack_received:
        return jsonify({"status": "WAITING"})

    receiver_info = state.receiver_info

    # Store receiver Kyber public key
    store_receiver_kyber_public_key(bytes.fromhex(receiver_info["kyber_public_key"]))
    app_state.peer_kyber_public_key = bytes.fromhex(receiver_info["kyber_public_key"])

    return jsonify({"status": "ACKNOWLEDGED"})