from app.services.encryption_service import aes_encrypt_file,aes_decrypt_file
from app.services.kem_service import rsa_encrypt_key, rsa_decrypt_key
from app.services.signature_service import sign_hash,verify_signature
from app.utils.helpers import sha256_hash_file


def encrypt_file_workflow(
    input_path,
    output_dir,
    rsa_public_key,
    signing_private_key
):
    # 1. AES encrypt file
    encrypted_path, aes_key = aes_encrypt_file(input_path, output_dir)

    # 2. RSA encrypt AES key (KEM)
    encrypted_aes_key = rsa_encrypt_key(aes_key, rsa_public_key)

    # 3. Hash encrypted file
    file_hash = sha256_hash_file(encrypted_path)

    # 4. Sign hash
    signature = sign_hash(file_hash, signing_private_key)

    return {
        "encrypted_file_path": encrypted_path,
        "encrypted_aes_key": encrypted_aes_key,
        "file_hash": file_hash,
        "signature": signature
    }

def decrypt_file_workflow(
    encrypted_file_path,
    encrypted_aes_key,
    signature,
    rsa_private_key,
    signer_public_key
):
    # 1. Hash encrypted file
    file_hash = sha256_hash_file(encrypted_file_path)

    # 2. Verify signature
    if not verify_signature(file_hash, signature, signer_public_key):
        raise Exception("Signature verification failed")

    # 3. Decrypt AES key
    aes_key = rsa_decrypt_key(encrypted_aes_key, rsa_private_key)

    # 4. AES decrypt file
    decrypted_path = aes_decrypt_file(
        encrypted_file_path,
        "decrypted_files",
        aes_key
    )

    return decrypted_path
