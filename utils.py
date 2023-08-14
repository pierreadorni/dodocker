import os
from Crypto.PublicKey import RSA


def check_if_key_exists(name):
    return os.path.exists(f"keys/{name}.pub")


def generate_key(name):
    key = RSA.generate(2048)
    with open(f"keys/{name}.pem", "wb") as f:
        f.write(key.export_key("PEM"))
    with open(f"keys/{name}.pub", "wb") as f:
        f.write(key.publickey().export_key("OpenSSH"))
