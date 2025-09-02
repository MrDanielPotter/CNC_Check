
import os, hashlib, secrets, json
from typing import Tuple, Optional

def pbkdf2_hash(pin: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, 200_000)
    return dk, salt

def verify_pin(pin: str, stored_hash_hex: str, salt_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac('sha256', pin.encode('utf-8'), salt, 200_000)
    return dk.hex() == stored_hash_hex

def init_default_pins(db):
    # If no pins, set defaults and require change on first admin open
    if db.get_setting("master_pin_hash") is None:
        h, s = pbkdf2_hash("2468")
        db.set_setting("master_pin_hash", h.hex())
        db.set_setting("master_pin_salt", s.hex())
    if db.get_setting("admin_pin_hash") is None:
        h, s = pbkdf2_hash("8642")
        db.set_setting("admin_pin_hash", h.hex())
        db.set_setting("admin_pin_salt", s.hex())
    if db.get_setting("pins_must_change") is None:
        db.set_setting("pins_must_change", "1")
