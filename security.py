import json
import machineid
import hashlib
import secrets
import sys
import os
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Util.Padding import pad, unpad
import base64
from loguru import logger
import httpx

logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <cyan> SECURITY </cyan> | <level>{level: <8}</level> | <level>{message}</level>",
)

ENDPOINT = "https://not.available.in.oss.invalid/api/client/v2"
RSA_PUBKEY = """NOT AVAILABLE IN OSS"""

SALT = "BHYG_OSS_SALT"
MACHINE_ID = hashlib.sha256(machineid.hashed_id().encode()+SALT.encode()).hexdigest()
HASHED_MACHINE_ID = hashlib.sha256(MACHINE_ID.encode()).hexdigest()[:7]

FALLBACK_POLICY = {
    "allow_run": False
}

FAILED_TIME = 0

POLICY = FALLBACK_POLICY

def get_machine_id() -> str:
    return HASHED_MACHINE_ID

def get_policy_value(key: str, default=None):
    # NOT AVAILABLE IN OSS
    raise Exception("NOT AVAILABLE IN OSS")

def fetch_policy(version: str) -> dict:
    # NOT AVAILABLE IN OSS
    raise Exception("NOT AVAILABLE IN OSS")
    
def heartbeat(version: str, uid: str):
    # NOT AVAILABLE IN OSS
    raise Exception("NOT AVAILABLE IN OSS")