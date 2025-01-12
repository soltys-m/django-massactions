import random
import string
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


def encrypt_string(string_to_encrypt):
    key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    string_to_encrypt = pad(string_to_encrypt.encode(), 16)
    cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(string_to_encrypt)).decode('utf-8') + key


def decrypt_string(string_to_decrypt):
    key = string_to_decrypt[-16:]
    enc = base64.b64decode(string_to_decrypt[:-16])
    cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
    return unpad(cipher.decrypt(enc), 16).decode('utf-8')