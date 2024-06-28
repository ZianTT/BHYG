# -*- coding: UTF-8 -*-
# Contains global variables
# Copyright (c) 2023-2024 ZianTT, FriendshipEnder

import sys
import os
import json

import inquirer

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration

from login import *

from globals import *
from utility import utility

from utils import prompt, save, load

import time
from i18n import i18n
i18n_lang = "中文"

def agree_terms():
    global i18n_lang
    while True:
        agree_prompt = input(
            i18n[i18n_lang]["eula"])
        if "同意" in agree_prompt and "死妈" in agree_prompt and "黄牛" in agree_prompt and "不" not in agree_prompt:
            break
        else:
            logger.error(i18n[i18n_lang]["wrong_input"])
    with open("agree-terms", "w") as f:
        import machineid
        f.write(machineid.id())
    logger.info(i18n[i18n_lang]["agree_eula"])

def init():
    global i18n_lang
    logger.remove(handler_id=0)
    if sys.argv[0].endswith(".py"):
        level = "DEBUG"
        format = "DEBUG MODE | <green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>"
        environment = "development"
        print("WARNING: YOU ARE IN DEBUG MODE")
    else:
        level = "INFO"
        format = "<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>"
        environment = "production"
    handler_id = logger.add(
        sys.stderr,
        format=format,
        level=level,  # NOTE: logger level
    )

    if not os.path.exists("agree-terms"):
        agree_terms()
    else:
        with open("agree-terms", "r") as f:
            hwid = f.read()
            import machineid
            if hwid != machineid.id():
                agree_terms()
                with open("agree-terms", "w") as f:
                    f.write(machineid.id())
    version = "v0.8.4"

    sentry_sdk.init(
        dsn="https://9c5cab8462254a2e1e6ea76ffb8a5e3d@sentry-inc.bitf1a5h.eu.org/3",
        release=version,
        profiles_sample_rate=1.0,
        enable_tracing=True,
        integrations=[
            LoguruIntegration(
                level=LoggingLevels.DEBUG.value, event_level=LoggingLevels.CRITICAL.value
            ),
        ],
        sample_rate=1.0,
        environment=environment
    )
    with sentry_sdk.configure_scope() as scope:
        scope.add_attachment(path="data")

    import machineid
    sentry_sdk.set_user({"hwid": machineid.id()[:16]})
    return version, sentry_sdk

def check_update(version):
    global i18n_lang
    try:
        import requests
        data = requests.get("https://api.github.com/repos/biliticket/BHYG/releases/latest",
                            headers={"Accept": "application/vnd.github+json"}).json()
        if data["tag_name"] != version:

            import platform
            if platform.system() == "Windows":
                name = "BHYG-Windows.exe"
            elif platform.system() == "Linux":
                name = "BHYG-Linux"
            elif platform.system() == "Darwin":
                print(platform.machine())
                if "arm" in platform.machine():
                    name = "BHYG-macOS-Apple_Silicon"
                elif "64" in platform.machine():
                    name = "BHYG-macOS-Intel"
                else:
                    name = "BHYG-macOS"
            else:
                name = "BHYG"
            find = False
            force = False
            for distribution in data["assets"]:
                if distribution["name"] == name:
                    logger.warning(
                        i18n[i18n_lang]["new_version_1"].format(data['tag_name'], distribution['browser_download_url'], distribution['size'] / 1024 / 1024))
                    if data['body'] != "":
                        logger.warning(i18n[i18n_lang]["new_version_notify"].format(data['body']))
                    if "force" in data["body"] or "强制" in data["body"]:
                        force = True
                    find = True
                    break
            if not find:
                logger.warning(i18n[i18n_lang]["new_version_2"].format(data['tag_name'], data['html_url']))
                if data['body'] != "":
                    logger.warning(i18n[i18n_lang]["new_version_notify"].format(data['body']))
                    if "force" in data["body"] or "强制" in data["body"]:
                        force = True    
                find = True
            if force:
                logger.warning(i18n[i18n_lang]["force_update_1"])
                logger.info(i18n[i18n_lang]["force_update_2"])
                while True:
                    pass
    except KeyboardInterrupt:
        logger.error(i18n[i18n_lang]["update_interrupted"])
        raise KeyboardInterrupt
    except:
        try:
            logger.warning(i18n[i18n_lang]["update_fail"])
            if not os.path.exists("skip-update"):
                logger.error(i18n[i18n_lang]["force_require_update"])
                while True:
                    pass
            else:
                logger.warning(i18n[i18n_lang]["update_passed"])
        except KeyboardInterrupt:
            logger.error(i18n[i18n_lang]["update_interrupted"])
            raise KeyboardInterrupt


class HygException(Exception):
    pass


def load_config():
    global i18n_lang
    go_utility = False
    if os.path.exists("config.json"):
        logger.info(i18n[i18n_lang]["welcome_new_version"])
        if os.path.isdir("data"):
            import shutil
            shutil.rmtree("data")
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            save(config)
        os.remove("config.json")
        logger.info(i18n[i18n_lang]["new_version_ok"])
    if os.path.exists("share.json"):
        logger.info(i18n[i18n_lang]["check_share"])
        with open("share.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            save(config)
        os.remove("share.json")
    if os.path.isdir("data"):
        import shutil
        shutil.rmtree("data")
    if os.path.exists("data"):
        run_info = prompt([
            inquirer.List(
                "run_info",
                message=i18n[i18n_lang]["select_setting"],
                choices=[i18n[i18n_lang]["select_keep_all"],
                         i18n[i18n_lang]["select_keep_login"],
                         i18n[i18n_lang]["select_new_boot"],
                         i18n[i18n_lang]["select_tools"],
                         i18n[i18n_lang]["select_tools_relogin"],
                         i18n[i18n_lang]["select_reset"],
                         "语言设置/Language setting"],
                default= i18n[i18n_lang]["select_keep_all"]
            )]
        )["run_info"]
        if run_info == i18n[i18n_lang]["select_new_boot"]:
            logger.info(i18n[i18n_lang]["select_new_boot_msg"])
            temp = load()
            config = {}
            if "pushplus" in temp:
                config["pushplus"] = temp["pushplus"]
            if "ua" in temp:
                config["ua"] = temp["pushplus"]
            if "captcha" in temp:
                config["captcha"] = temp["captcha"]
            if "rrocr" in temp:
                config["rrocr"] = temp["rrocr"]
            if "proxy" in temp:
                config["proxy"] = temp["proxy"]
                if "proxy_auth" in temp:
                    config["proxy_auth"] = temp["proxy_auth"]
                if "proxy_channel" in temp:
                    config["proxy_channel"] = temp["proxy_channel"]
            use_login = False
        elif run_info == i18n[i18n_lang]["select_keep_login"]:
            logger.info(i18n[i18n_lang]["select_keep_login_msg"])
            temp = load()
            config = {}
            if "gaia_vtoken" in temp:
                config["gaia_vtoken"] = temp["gaia_vtoken"]
            if "ua" in temp:
                config["ua"] = temp["ua"]
            if "cookie" in temp:
                config["cookie"] = temp["cookie"]
            if "pushplus" in temp:
                config["pushplus"] = temp["pushplus"]
            if "phone" in temp:
                config["phone"] = temp["phone"]
            if "captcha" in temp:
                config["captcha"] = temp["captcha"]
            if "rrocr" in temp:
                config["rrocr"] = temp["rrocr"]
            if "proxy" in temp:
                config["proxy"] = temp["proxy"]
                if "proxy_auth" in temp:
                    config["proxy_auth"] = temp["proxy_auth"]
                if "proxy_channel" in temp:
                    config["proxy_channel"] = temp["proxy_channel"]
            use_login = True
        elif run_info == i18n[i18n_lang]["select_keep_all"]:
            logger.info(i18n[i18n_lang]["select_keep_all_msg"])
            config = load()
            use_login = True
        elif run_info == i18n[i18n_lang]["select_tools"]:
            logger.info(i18n[i18n_lang]["select_tools"])
            go_utility = True
            use_login = True
            config = load()
        elif run_info == i18n[i18n_lang]["select_tools_relogin"]:
            logger.info(i18n[i18n_lang]["select_tools_relogin"])
            go_utility = True
            use_login = False
            config = {}
        elif run_info == i18n[i18n_lang]["select_reset"]:
            choice = prompt([inquirer.List("again", message=i18n[i18n_lang]["select_reset_msg"],
                choices=[i18n[i18n_lang]["no"], i18n[i18n_lang]["yes"]], default=i18n[i18n_lang]["no"])])[
                "again"]
            if choice == i18n[i18n_lang]["yes"]:
                os.remove("language")
                os.remove("data")
                os.remove("agree-terms")
                config = {}
                logger.info(i18n[i18n_lang]["select_reset_ok"])
            else:
                logger.info(i18n[i18n_lang]["select_reset_cancel"])
            return
        elif run_info == "语言设置/Language setting":
            i18n_lang = inquirer.prompt([
                inquirer.List(
                    name="lang_select",
                    message="Please select language",
                    choices=["中文", "English", "中文(猫娘)"],
                )]
            )["lang_select"]
            with open("language", "w", encoding="utf-8") as f:
                f.write(i18n_lang)
                f.close
            config = load()
            go_utility = True
            use_login = True
    else:
        save({})
        config = {}
    import ntplib
    c = ntplib.NTPClient()
    ntp_servers = (
        "ntp.ntsc.ac.cn",           #//Zhejiang ping: 27.75 ms
        "time.pool.aliyun.com",     #//Zhejiang ping:  32.5 ms
        "time1.cloud.tencent.com",  #//Zhejiang ping:    35 ms
        "asia.pool.ntp.org",        #//Zhejiang ping:    37 ms
        "edu.ntp.org.cn",           #//Zhejiang ping:    41 ms
        "cn.ntp.org.cn",            #//Zhejiang ping:    41 ms | ipv6 | 有时候抽风
        "cn.pool.ntp.org",          #//Zhejiang ping:    50 ms | 有时候抽风
        "ntp.tuna.tsinghua.edu.cn", #//Zhejiang ping:    55 ms | ipv6
        "time.asia.apple.com",      #//Zhejiang ping: 78.75 ms
        "time.windows.com",         #//Zhejiang ping:    89 ms
    )
    skip = 0
    for i in range(10):
        try:
            response = c.request(ntp_servers[i], timeout=1)
        except Exception:
            skip += 1
        else:
            break
    if skip >= 10:
        logger.error(i18n[i18n_lang]["time_sync_fail"])
        config["time_offset"] = 0
    else:
        time_offset = response.offset
        if time_offset > 0.5:
            logger.warning(i18n[i18n_lang]["time_sync_delta"].format(time_offset))
        config["time_offset"] = time_offset
    while True:
        if "cookie" not in config or not use_login:
            config["cookie"] = interactive_login(sentry_sdk)
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0",
            "Cookie": config["cookie"],
        }
        user = requests.get(
            "https://api.bilibili.com/x/web-interface/nav", headers=headers
        )
        user = user.json()
        if user["data"]["isLogin"]:
            logger.success(i18n[i18n_lang]["user"] +' '+ user["data"]["uname"] +' '+ i18n[i18n_lang]["login_success"])
            if user["data"]["vipStatus"] != 0:
                logger.info(i18n[i18n_lang]["user_bigvip"].format((user['data']['vipDueDate'] / 1000 - time.time()) / 60 / 60 / 24))
            import machineid
            sentry_sdk.set_user(
                {
                    "username": user["data"]["mid"],
                    "hwid": machineid.id()[:16]
                }
            )
            if "hunter" in config:
                logger.success(i18n[i18n_lang]["hunter_mode"])
                logger.info(i18n[i18n_lang]["hunter_grade"].format(config['hunter']))
            save(config)
            break
        else:
            logger.error(i18n[i18n_lang]["login_failure"])
            use_login = False
            config.pop("cookie")
            save(config)
    if go_utility:
        utility(config)
        return load_config()
    return config
