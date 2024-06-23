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

if not os.path.exists("agree-terms") and level is not "DEBUG":
    while True:
        agree_prompt = input("欢迎使用BHYG软件，使用前请阅读EULA(https://github.com/biliticket/BHYG)。若您使用时遇到问题，请查阅biliticket文档(https://docs.bitf1a5h.eu.org/)\n特别提醒，根据EULA，严禁任何形式通过本软件盈利。若您同意本软件EULA，请键入：我已阅读并同意EULA，黄牛倒卖狗死妈\n")
        if agree_prompt != "我已阅读并同意EULA，黄牛倒卖狗死妈":
            logger.error("输入不正确，请重试")
        else:
            break
    with open("agree-terms", "w") as f:
        f.write("")
    logger.info("已同意EULA")

sentry_sdk.init(
    dsn="https://9c5cab8462254a2e1e6ea76ffb8a5e3d@sentry-inc.bitf1a5h.eu.org/3",
    release="v0.7.5",
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
            if "gaia_vtoken" in temp:
                config["gaia_vtoken"] = temp["gaia_vtoken"]
            if "ua" in temp:
                config["ua"] = temp["ua"]
            if "cookie" in temp:
                config["cookie"] = temp["cookie"]
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
    import ntplib
    c = ntplib.NTPClient()
    response = c.request('pool.ntp.org')
    import time
    time_offset = response.offset
    if time_offset > 0.5:
        logger.warning(f"当前时间偏移：{time_offset:.2f}秒，建议校准时间")
    config["time_offset"] = time_offset
    while True:
            if "cookie" not in config or not use_login:
                config["cookie"] = interactive_login(sentry_sdk)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BHYG/0.7.5",
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
                if "hunter" in config:
                    logger.success("已启用猎手模式")
                    logger.info(f"战绩：{config['hunter']}张")           
                break
            else:
                logger.error("登录失败")
                use_login = False
                config.pop("cookie")
    if go_utility:
        utility(config)
        return load_config()
    return config
