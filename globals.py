# -*- coding: UTF-8 -*-
# Contains global variables


import sys
import os
import json 

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration

from login import *

import inquirer

from utility import utility

logger.remove(handler_id=0)
if sys.argv[0].endswith(".py"):
    level = "DEBUG"
    format = "DEBUG MODE | <green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    print("WARNING: YOU ARE IN DEBUG MODE")
else:
    level = "INFO"
    format = "<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>"
handler_id = logger.add(
    sys.stderr,
    format=format,
    level=level,  # NOTE: logger level
)

if os.path.exists("upload-error") or level == "DEBUG":
    sample_rate=1
    if level == "DEBUG":
        logger.debug("ERROR REPORTING IS ENABLED BY FORCE IN DEBUG MODE")
elif os.path.exists("do-not-upload-error"):
    sample_rate=0
else:    
    is_upload_error = inquirer.prompt([inquirer.List("is_upload_error", message="可选的错误上传：您是否选择上传可能遇到的错误以帮助我们改善脚本？", choices=["是", "否"], default="是")])
    if is_upload_error["is_upload_error"] == "否":
        logger.info("已选择不上传错误")
        sample_rate=0
        with open("do-not-upload-error", "w") as f:
            f.write("")
    else:
        logger.info("已选择上传错误")
        logger.info("感谢您的理解与支持！")
        sample_rate=1
        with open("upload-error", "w") as f:
            f.write("")
sentry_sdk.init(
    dsn="https://9c5cab8462254a2e1e6ea76ffb8a5e3d@sentry-inc.bitf1a5h.eu.org/3",
    release="v0.7.3",
    
    enable_tracing=True,
    integrations=[
        LoguruIntegration(
            level=LoggingLevels.DEBUG.value, event_level=LoggingLevels.CRITICAL.value
        ),
    ],
    sample_rate=sample_rate,
)
with sentry_sdk.configure_scope() as scope:
    scope.add_attachment(path="config.json")

bhyg_username = "未知用户"
uid = None

class HygException(Exception):
    pass


def load_config(): 
    go_utility = False
    if os.path.exists("config.json"):
        run_info = inquirer.prompt([
            inquirer.List(
                "run_info",
                message="请选择运行设置",
                choices=["延续上次启动所有配置", "保留登录信息重新配置", "全新启动", "进入账户实用工具", "进入账户实用工具（重新登录）"],
                default="延续上次启动所有配置"
            )]
        )["run_info"]
        if run_info == "全新启动":
            logger.info("重新配置")
            config = {}
            use_login = False
        elif run_info == "保留登录信息重新配置":
            logger.info("只沿用登录信息")
            with open("config.json", "r", encoding="utf-8") as f:
                temp = json.load(f)
                config = {}
                if "gaia_vtoken" in temp:
                    config["gaia_vtoken"] = temp["gaia_vtoken"]
            use_login = True
        elif run_info == "延续上次启动所有配置":
            logger.info("使用上次的配置文件")
            # 读取config.json，转为dict并存入config
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            use_login = True
        elif run_info == "进入账户实用工具":
            logger.info("进入账户实用工具")
            go_utility = True
            use_login = True
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        elif run_info == "进入账户实用工具（重新登录）":
            logger.info("进入账户实用工具（重新登录）")
            go_utility = True
            use_login = False
            config = {}
    else:
        # 不存在则创建config.json
        with open("config.json", "w", encoding="utf-8") as f:
            f.write("{}")
        config = {}

    while True:
            if os.path.exists("login-info") and use_login:
                with open("login-info", "r", encoding="utf-8") as f:
                    config["cookie"] = f.read()
            else:
                config["cookie"] = interactive_login()
                with open("login-info", "w", encoding="utf-8") as f:
                    f.write(config["cookie"])
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BHYG/0.7.3",
                "Cookie": config["cookie"],
            }
            user = requests.get(
                "https://api.bilibili.com/x/web-interface/nav", headers=headers
            )
            user = user.json()
            if user["data"]["isLogin"]:
                logger.success("用户 " + user["data"]["uname"] + " 登录成功")
                sentry_sdk.set_user(
                    {
                        "username": user["data"]["mid"]
                    }
                )
                break
            else:
                logger.error("登录失败")
                use_login = False
                config.pop("cookie")
    if go_utility:
        utility(config)
        return load_config()
    return config
