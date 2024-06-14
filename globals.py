# -*- coding: UTF-8 -*-
# Contains global variables


import sys
import os
import json 

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.loguru import LoggingLevels, LoguruIntegration

sentry_sdk.init(
    dsn="https://978fc0de4c8c46d597f52934a393ea20@o4504797893951488.ingest.us.sentry.io/4505567308087296",
    release="v0.7.0",
    # Enable performance monitoring
    enable_tracing=True,
    integrations=[
        LoguruIntegration(
            level=LoggingLevels.DEBUG.value, event_level=LoggingLevels.CRITICAL.value
        ),
    ],
)
with sentry_sdk.configure_scope() as scope:
    scope.add_attachment(path="config.json")

logger.remove(handler_id=0)
handler_id = logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",  # NOTE: logger level
)


bhyg_username = "未知用户"
uid = None

class HygException(Exception):
    pass


def load_config(): 
    # 判断是否存在config.json
    if os.path.exists("config.json"):
        is_use_config = input(
            "已存在上一次的配置文件，是否沿用全部或只沿用登录信息（包括风控信息）？(Y/l/n)"
        )
        if is_use_config == "n":
            logger.info("重新配置")
            config = {}
        elif is_use_config == "l":
            logger.info("只沿用登录信息")
            with open("config.json", "r", encoding="utf-8") as f:
                config = {}
                try:
                    temp = json.load(f)
                    config["cookie"] = temp["cookie"]
                    if "gaia_vtoken" in temp:
                        config["gaia_vtoken"] = temp["gaia_vtoken"]
                except Exception as e:
                    logger.error(e)
                    logger.error("读取cookie失败，重新配置")
                    config = {}
        else:
            if is_use_config.lower() == "y":
                logger.info("使用上次的配置文件")
            else:
                logger.info("已默认使用上次的配置文件")
            # 读取config.json，转为dict并存入config
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
    else:
        # 不存在则创建config.json
        with open("config.json", "w", encoding="utf-8") as f:
            f.write("{}")
        config = {}

    return config
