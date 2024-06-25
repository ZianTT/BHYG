import inquirer
import requests
from loguru import logger

def prompt(prompt):
    data = inquirer.prompt(prompt)
    if data is None:
        raise KeyboardInterrupt
    return data

def utility(config):
    import base64
    def save(data: dict):
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
            f.write(iv+"%"+data)
        return
    def add_buyer(headers):
        name = input("请输入购票人姓名：")
        id_type = prompt([inquirer.List("id_type", message="请选择证件类型", choices=["0. 身份证", "1. 护照", "2. 港澳居民往来内地通行证", "3. 台湾居民往来大陆通行证"], default="身份证"),
        ])
        personal_id = input("请输入购票人证件号码：")
        tel = input("请输入购票人手机号码：")
        data = {
            "name": name,
            "tel": tel,
            "id_type": id_type["id_type"].split(".")[0],
            "personal_id": personal_id,
            "is_default": "0",
            "src": "ticket"
        }
        logger.debug(data)
        response = requests.post("https://show.bilibili.com/api/ticket/buyer/create", headers=headers, data=data)
        if response.json()["errno"] == 0:
            logger.info("添加成功")
        else:
            logger.error(f"{response.json()['errno']}: {response.json()['msg']}")
            return add_buyer(headers)

    def modify_ua():
        ua = input("请输入您要覆盖的UA：")
        config["ua"] = ua

    def modify_gaia_vtoken():
        gaia_vtoken = input("请输入您的gaia_vtoken：")
        config["gaia_vtoken"] = gaia_vtoken
    
    def hunter_mode():
        config["hunter"] = 0
        logger.info("猎手模式已开启（归零）")

    def hunter_mode_off():
        if "hunter" in config:
            config.pop("hunter")
        logger.info("猎手模式已关闭")

    def share_mode(config):
        import json
        json.dump(config, open("share.json", "w"))
        import os
        os.remove("data")
        logger.info("分享模式已启动")
        logger.info("自动退出中……")
        import sys
        sys.exit(0)
        return

    def pushplus_config(config):
        token = input("请输入您的PushPlus Token(留空关闭)：")
        if token == "":
            if "pushplus" in config:
                config.pop("pushplus")
            logger.info("PushPlus推送已关闭")
            save(config)
            return
        config["pushplus"] = token
        logger.info("PushPlus推送已开启")
        save(config)

    def save_phone(config):
        phone = input("请输入您的手机号码：")
        config["phone"] = phone
        logger.info("手机号码已保存")
        save(config)
    
    headers = {
        "Cookie": config["cookie"],
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BHYG/0.7.7",
        "Referer": "https://show.bilibili.com"
    }
    select = prompt([
        inquirer.List(
            "select",
            message="请选择您要使用的实用工具",
            choices=["添加购票人", "覆盖默认UA", "覆盖gaia_vtoken", "开启猎手模式(计数清零)", "关闭猎手模式", "分享模式", "PushPlus推送", "预填绑定手机号", "返回"],
        )])
    if select["select"] == "添加购票人":
        add_buyer(headers)
        return utility(config)
    elif select["select"] == "覆盖默认UA":
        modify_ua()
        return utility(config)
    elif select["select"] == "覆盖gaia_vtoken":
        modify_gaia_vtoken()
        return utility(config)
    elif select["select"] == "开启猎手模式(计数清零)":
        hunter_mode()
        return utility(config)
    elif select["select"] == "关闭猎手模式":
        hunter_mode_off()
        return utility(config)
    elif select["select"] == "分享模式":
        share_mode(config)
        return utility(config)
    elif select["select"] == "PushPlus推送":
        pushplus_config(config)
        return utility(config)
    elif select["select"] == "预填绑定手机号":
        save_phone(config)
    elif select["select"] == "返回":
        return
    else:
        logger.error("暂不支持此功能")
        return utility()