import os
import uuid
import base64
import requests
from flask import Blueprint, request, jsonify, current_app
from app.extensions import app_state
import urllib.parse


# PQC workflow services
from app.services.pqc_workflow_service import (
    pqc_encrypt_file_workflow,
    pqc_decrypt_file_workflow
)

# Key storage helpers (used during handshake elsewhere)
from app.services.pqc_key_service import (
    store_receiver_kyber_public_key,
    store_sender_dilithium_public_key
)

# ------------------------------------------------------
# Blueprint
# ------------------------------------------------------
file_pqc_bp = Blueprint("file_pqc", __name__)

# ======================================================
# SENDER: Encrypt file using PQC
# ======================================================
@file_pqc_bp.route("/pqc/encrypt", methods=["POST"])
def pqc_encrypt_file():
    # if app_state.role != "SENDER":
    #     return jsonify({"error": "Not in sender mode"}), 403
    
    if "file" not in request.files:
        return jsonify({"error": "File missing"}), 400

    uploaded_file = request.files["file"]
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    input_path = os.path.join(upload_dir, uploaded_file.filename)
    uploaded_file.save(input_path)

    try:
        # Full PQC encryption workflow
        result = pqc_encrypt_file_workflow(input_path)
    except Exception as e:
        print(f"Error during PQC encryption: {e}")
        return jsonify({"error": str(e)}), 500

    # Delete original file after encryption
    try:
        os.remove(input_path)
    except Exception as e:
        print(f"Failed to delete original file: {e}")

    # Read encrypted file → base64
    with open(result["encrypted_file_path"], "rb") as f:
        encrypted_b64 = base64.b64encode(f.read()).decode("utf-8")
    print(encrypted_b64[:100] + "...")  # Print first 100 chars for debugging
    return jsonify({
        "message": "File encrypted using PQC",
        "encrypted_file": encrypted_b64,
        "encrypted_file_name": os.path.basename(result["encrypted_file_path"]),
        "kyber_ciphertext": result["kyber_ciphertext"].hex(),
        "signature": base64.b64encode(
            result["signature"]
        ).decode("utf-8"),
        "original_filename": uploaded_file.filename
    }), 200


# ======================================================
# SENDER → RECEIVER: Send encrypted file
# ======================================================
@file_pqc_bp.route("/pqc/send-file", methods=["POST"])
def pqc_send_file():
    """
    Sender backend → Receiver backend
    Sends encrypted file + Kyber ciphertext + Dilithium signature
    """
    data = request.get_json()
    
    if not data:
        print("Invalid JSON payload received")
        return jsonify({"error": "Invalid JSON payload"}), 400

    receiver_api = data.get("receiver_api")
    encrypted_file_b64 = data.get("encryptedFile")  # ← Changed: get base64 file from JSON
    encrypted_file_name = data.get("encrypted_file_name")
    signature = data.get("signature")
    kyber_ciphertext = data.get("kyber_ciphertext")
    original_filename = data.get("original_filename")
    print("encrypted_file_b64 length:", len(encrypted_file_b64) if encrypted_file_b64 else "None")
    if not all([
        receiver_api,
        encrypted_file_b64,  # ← Changed: check for base64 file
        encrypted_file_name,
        signature,
        kyber_ciphertext,
        original_filename
    ]):
        print("Missing required fields in payload:", data)
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Decode base64 encrypted file to raw bytes
        encrypted_file_bytes = base64.b64decode(encrypted_file_b64)
        
        # Prepare multipart form data
        files = {
            "file": (
                encrypted_file_name,
                encrypted_file_bytes,  # ← Raw bytes, not base64
                "application/octet-stream"
            )
        }
        
        form_data = {
            "signature": signature,  # Keep as base64 string
            "kyber_ciphertext": kyber_ciphertext,  # Keep as base64 string
            "original_filename": original_filename
        }

        print(f"Sending to receiver: {receiver_api}/pqc/decrypt")
        response = requests.post(
            f"{receiver_api}/pqc/decrypt",
            files=files,
            data=form_data,
            timeout=300
        )

        # Forward receiver response to sender UI
        if response.status_code != 200:
            print(f"Receiver error: {response.status_code} - {response.text}")
            return jsonify({
                "error": "Receiver failed to decrypt",
                "receiver_status": response.status_code,
                "receiver_response": response.text
            }), 500

        print("File sent and decrypted successfully")
        return jsonify({
            "message": "File sent successfully",
            "receiver_response": response.json()
        }), 200

    except base64.binascii.Error as e:
        print(f"Base64 decode error: {str(e)}")
        return jsonify({
            "error": "Invalid base64 encoding",
            "details": str(e)
        }), 400
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return jsonify({
            "error": "Failed to contact receiver",
            "details": str(e)
        }), 500
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

# ======================================================
# RECEIVER: Decrypt file using PQC
# ======================================================
@file_pqc_bp.route("/pqc/decrypt", methods=["POST"])
def pqc_decrypt_file():
    # if app_state.role != "RECEIVER":
    #     return jsonify({"error": "Not in receiver mode"}), 403
    
    if "file" not in request.files:
        return jsonify({"error": "Encrypted file missing"}), 400

    encrypted_file = request.files["file"]
    signature_b64 = request.form.get("signature")
    kyber_ct_b64 = request.form.get("kyber_ciphertext")
    original_filename = request.form.get(
        "original_filename", "received_file"
    )

     # Print first 100 chars for debugging
    if not signature_b64 or not kyber_ct_b64:
        print("Missing signature or Kyber ciphertext in form data")
        return jsonify({"error": "Missing signature or Kyber ciphertext"}), 400
    print(f"kyber_ct_b64: {kyber_ct_b64[:100]}...")  # Print first 100 chars for debugging
    # Decode Base64 inputs
    kyber_ct = bytes.fromhex(kyber_ct_b64)  
    print(f"Kyber ciphertext length: {len(kyber_ct)} bytes")
    try:
        signature = base64.b64decode(signature_b64)
        
    except Exception:
        print("Invalid Base64 encoding for signature or Kyber ciphertext")
        return jsonify({"error": "Invalid Base64 encoding"}), 400

    # Save encrypted file exactly as received
    encrypted_dir = current_app.config["ENCRYPTED_FOLDER"]
    os.makedirs(encrypted_dir, exist_ok=True)
    encrypted_path = os.path.join(
        encrypted_dir,
        f"recv_{uuid.uuid4().hex}.enc"
    )
    
    encrypted_file.stream.seek(0)
    with open(encrypted_path, "wb") as f:
        f.write(encrypted_file.read())

    # Store Kyber ciphertext for decapsulation
    kyber_ct_path = os.path.join(
        current_app.config["PQC_KEY_FOLDER"],
        "sender_kyber_ct.bin"
    )
    with open(kyber_ct_path, "wb") as f:
        f.write(kyber_ct)
    print(f"Kyber ciphertext stored for decapsulation at: {kyber_ct_path}")
    try:
        decrypted_path = pqc_decrypt_file_workflow(
            encrypted_file_path=encrypted_path,
            signature=signature,
            original_filename=original_filename
        )
        print("File decrypted successfully")
        
        # Delete encrypted file after successful decryption
        os.remove(encrypted_path)
        
    except Exception as e:
        print(f"Decryption error: {str(e)}")
        return jsonify({"error": str(e)}), 400

    # Read decrypted file for queue storage
    with open(decrypted_path, "rb") as f:
        decrypted_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    file_size = os.path.getsize(decrypted_path)
    file_id = str(uuid.uuid4())

    # Initialize queue if not exists
    if not hasattr(app_state, 'pqc_received_files_queue'):
        app_state.pqc_received_files_queue = []

    # Add to queue
    app_state.pqc_received_files_queue.append({
        "id": file_id,
        "filename": original_filename,
        "kyber_ciphertext": kyber_ct_b64,
        "signature": signature_b64,
        "decrypted_file": decrypted_b64,
        "file_size": file_size,
        "path": decrypted_path,
        "status": "READY"
    })

    return jsonify({
        "message": "File decrypted and stored",
        "file_id": file_id
    }), 200


# ======================================================
# RECEIVER: Get next file from queue
# ======================================================
@file_pqc_bp.route("/pqc/next-file", methods=["POST"])
def pqc_next_file():
    """Get next PQC-encrypted file from queue and delete from backend"""
    if app_state.role != "RECEIVER":
        return jsonify({"error": "Not in receiver mode"}), 403

    if not hasattr(app_state, 'pqc_received_files_queue') or not app_state.pqc_received_files_queue:
        return jsonify({"message": "No files available"}), 204  # No Content

    # Get first file from queue
    file_entry = app_state.pqc_received_files_queue.pop(0)
    
    # Delete file from disk
    try:
        if os.path.exists(file_entry["path"]):
            os.remove(file_entry["path"])
    except Exception as e:
        print(f"Failed to delete file from disk: {e}")
    
    # Return entire file data
    return jsonify({
        "id": file_entry["id"],
        "filename": file_entry["filename"],
        "file_data": file_entry["decrypted_file"],
        "file_size": file_entry["file_size"],
        "kyber_ciphertext": file_entry["kyber_ciphertext"],
        "signature": file_entry["signature"]
    }), 200