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
