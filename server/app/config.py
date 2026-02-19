import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "uploads")
    ENCRYPTED_FOLDER = os.path.join(BASE_DIR, "..", "encrypted_files")
    DECRYPTED_FOLDER = os.path.join(BASE_DIR,"..","decrypted_files")
    PQC_KEY_FOLDER = os.path.join(BASE_DIR, "..", "pqc_keys")

    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 20 MBq
