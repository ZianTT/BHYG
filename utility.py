import inquirer
import requests
from loguru import logger

from utils import prompt, save, load

from i18n import i18n

def utility(config):
    import base64
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
    
    def use_proxy(config):
        choice = prompt([inquirer.List("proxy", message=i18n["zh"]["input_is_use_proxy"], choices=[i18n["zh"]["yes"], i18n["zh"]["no"]], default=i18n["zh"]["no"])])["proxy"]
        if choice == i18n["zh"]["yes"]:
            while True:
                while True:
                    try:
                        config["proxy_auth"] = input(i18n["zh"]["input_proxy"]).split(" ")
                        assert len(config["proxy_auth"]) == 3
                    except:
                        logger.error(i18n["zh"]["wrong_proxy_format"])
                        continue
                config["proxy_channel"] = prompt([
                    inquirer.Text("proxy_channel", message=i18n["zh"]["input_proxy_channel"], validate=lambda _, x: x.isdigit())
                ])["proxy_channel"]
                config["proxy"] = True
                break
        else:
            config["proxy"] = False
        save(config)

    def captcha_mode(config):
        choice = prompt([inquirer.List("captcha", message=i18n["zh"]["input_use_captcha_mode"], choices=[
            i18n["zh"]["local_gt"],
            i18n["zh"]["rrocr"],
            i18n["zh"]["manual"],
        ], default=i18n["zh"]["manual"])])["captcha"]
        if choice == i18n["zh"]["local_gt"]:
            config["captcha"] = "local_gt"
        elif choice == i18n["zh"]["rrocr"]:
            config["captcha"] = "rrocr"
            config["rrocr_key"] = input("请输入RROCR KEY：")
        else:
            logger.error(i18n["zh"]["captcha_mode_not_supported"])
        save(config)

    headers = {
        "Cookie": config["cookie"],
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0",
        "Referer": "https://show.bilibili.com"
    }
    select = prompt([
        inquirer.List(
            "select",
            message="请选择您要使用的实用工具",
            choices=["添加购票人", "覆盖默认UA", "覆盖gaia_vtoken", "开启猎手模式(计数清零)", "关闭猎手模式", "分享模式", "PushPlus推送", "预填绑定手机号", "代理设置", "选择验证码模式", "返回"],
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
        return utility(config)
    elif select["select"] == "代理设置":
        use_proxy(config)
        return utility(config)
    elif select["select"] == "选择验证码模式":
        captcha_mode(config)
        return utility(config)
    elif select["select"] == "返回":
        return
    else:
        logger.error("暂不支持此功能")
        return utility()
