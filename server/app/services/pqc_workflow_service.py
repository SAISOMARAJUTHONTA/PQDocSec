from urllib import response

from flask import current_app
import os
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

# Key / KEM
from app.services.pqc_key_service import (
    sender_generate_shared_secret_and_ciphertext,
    receiver_derive_shared_secret_from_ciphertext
)

# Crypto
from app.services.crypto_service import (
    derive_aes_key_from_shared_secret,
    compute_hash_from_encrypted_file_and_kyber_ct
)

# AES encryption
from app.services.pqc_encryption_service import (
    encrypt_file_with_aes_key,
    decrypt_file_with_aes_key
)

# Signatures
from app.services.pqc_signature_service import (
    sign_hash_with_dilithium,
    verify_dilithium_signature
)
# Timer
import time

# ======================================================
# SENDER WORKFLOW (Encrypt + Sign)
# ======================================================

def pqc_encrypt_file_workflow(input_path: str):
    """
    PQC-based encryption workflow (Sender side)

    Returns:
        {
            encrypted_file_path,
            kyber_ciphertext,
            file_hash,
            signature
        }
    """
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    kyber_start = time.perf_counter_ns()
    # 1️⃣ Kyber encapsulation (shared secret + ciphertext)
    shared_secret, kyber_ct = sender_generate_shared_secret_and_ciphertext()
    kyber_end = time.perf_counter_ns()
    print(f"Kyber encapsulation time: {(kyber_end - kyber_start) / 1e6:.2f} ms")  # Debug print of time taken
    # 2️⃣ Derive AES key from shared secret
    print(f"Derived shared secret: {shared_secret.hex()}")  # Debug print of shared secret

    derive_start = time.perf_counter_ns()
    aes_key = derive_aes_key_from_shared_secret(shared_secret)
    derive_end = time.perf_counter_ns()
    print(f"AES key derivation time: {(derive_end - derive_start) / 1e6:.2f} ms")  # Debug print of time taken
    print(f"Derived AES key: {aes_key.hex()}")  # Debug print of AES key
    # 3️⃣ AES encrypt file
    
    aes_start = time.perf_counter_ns()
    encrypted_path = encrypt_file_with_aes_key(
        input_path,
        current_app.config["ENCRYPTED_FOLDER"],
        aes_key
    )
    aes_end = time.perf_counter_ns()
    print(f"AES encryption time: {(aes_end - aes_start) / 1e6:.2f} ms")  # Debug print of time taken

    # 4️⃣ Hash encrypted file + Kyber ciphertext
    hash_start = time.perf_counter_ns()
    file_hash = compute_hash_from_encrypted_file_and_kyber_ct(
        encrypted_path,
        f"{current_app.config['PQC_KEY_FOLDER']}/kyber_ct.bin"
    )
    hash_end = time.perf_counter_ns()
    print(f"Hash computation time: {(hash_end - hash_start) / 1e6:.2f} ms")  # Debug print of time taken

    # 5️⃣ Sign hash using Dilithium
    sign_start = time.perf_counter_ns()
    signature = sign_hash_with_dilithium(file_hash)
    sign_end = time.perf_counter_ns()
    print(f"Dilithium signature time: {(sign_end - sign_start) / 1e6:.2f} ms")  # Debug print of time taken

    data = {
        "file_name": os.path.basename(input_path),
        "key_encapsulation": (kyber_end - kyber_start) / 1e6,  # ms
        "derive_key": (derive_end - derive_start) / 1e6,       # ms
        "AES_encryption": (aes_end - aes_start) / 1e6,
        "Hash_generation": (hash_end - hash_start) / 1e6,
        "Sign_hash": (sign_end - sign_start) / 1e6              # ms
    }
    response = supabase.table("post-quantum encryption").insert(data).execute()

# Optional debug
    print("Supabase insert response:", response)

    return {
        "encrypted_file_path": encrypted_path,
        "kyber_ciphertext": kyber_ct,
        "shared_secret": shared_secret,
        "file_hash": file_hash,
        "signature": signature
    }


# ======================================================
# RECEIVER WORKFLOW (Verify + Decrypt)
# ======================================================

def pqc_decrypt_file_workflow(
    encrypted_file_path: str,
    signature: bytes,
    original_filename: str
):
    """
    PQC-based decryption workflow (Receiver side)

    Returns:
        decrypted_file_path
    """
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    # 1️⃣ Hash encrypted file + Kyber ciphertext
    hash_start = time.perf_counter_ns()
    file_hash = compute_hash_from_encrypted_file_and_kyber_ct(
        encrypted_file_path,
        f"{current_app.config['PQC_KEY_FOLDER']}/kyber_ct.bin"
    )
    hash_end = time.perf_counter_ns()
    print(f"Hash computation time: {(hash_end - hash_start) / 1e6:.2f} ms")  # Debug print of time taken

    # 2️⃣ Verify Dilithium signature
    verify_start = time.perf_counter_ns()
    if not verify_dilithium_signature(file_hash, signature):
        raise Exception("Signature verification failed")
    verify_end = time.perf_counter_ns()
    print(f"Dilithium signature verification time: {(verify_end - verify_start) / 1e6:.2f} ms")  # Debug print of time taken

    # 3️⃣ Kyber decapsulation (derive shared secret)
    kyber_start = time.perf_counter_ns()
    shared_secret = receiver_derive_shared_secret_from_ciphertext()
    kyber_end = time.perf_counter_ns()
    print(f"Kyber decapsulation time: {(kyber_end - kyber_start) / 1e6:.2f} ms")  # Debug print of time taken
    print(f"Derived shared secret: {shared_secret.hex()}")  # Debug print of shared secret

    # 4️⃣ Derive AES key from shared secret
    derive_start = time.perf_counter_ns()
    aes_key = derive_aes_key_from_shared_secret(shared_secret)
    derive_end = time.perf_counter_ns()
    print(f"AES key derivation time: {(derive_end - derive_start) / 1e6:.2f} ms")  # Debug print of time taken
    print(f"Derived AES key: {aes_key.hex()}")  # Debug print of AES key

    # 5️⃣ AES decrypt file
    aes_start = time.perf_counter_ns()
    decrypted_path = decrypt_file_with_aes_key(
        encrypted_file_path,
        current_app.config["DECRYPTED_FOLDER"],
        aes_key,
        original_filename
    )
    aes_end = time.perf_counter_ns()
    print(f"AES decryption time: {(aes_end - aes_start) / 1e6:.2f} ms")  # Debug print of time taken

    data = {
        "file_name": original_filename,
        "Hash_generation": (hash_end - hash_start) / 1e6,          # ms
        "Verify_signature": (verify_end - verify_start) / 1e6,     # ms
        "key_encapsulation": (kyber_end - kyber_start) / 1e6,
        "derive_key": (derive_end - derive_start) / 1e6,       # ms
        "AES_decryption": (aes_end - aes_start) / 1e6              # ms
    }

    response = supabase.table("post-quantum decryption").insert(data).execute()

# Optional debug
    print("Supabase insert response:", response)
    return {
        "decrypted_file_path": decrypted_path,
        "file_hash": file_hash,
        "shared_secret": shared_secret,
        "signature_verified": True,
        "original_filename": original_filename,
        # This can be added if needed for debugging       
    }