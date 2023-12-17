'''
Author: ZianTT 2508164094@qq.com
Date: 2023-07-25 17:08:39
LastEditors: ZianTT 2508164094@qq.com
LastEditTime: 2023-12-18 00:44:49
FilePath: \bilibili-hyg\main.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
# Copyright (c) 2023 ZianTT
# bilibili-hyg is licensed under Mulan PubL v2.
# You can use this software according to the terms and conditions of the Mulan PubL v2.
# You may obtain a copy of Mulan PubL v2 at:
#          http://license.coscl.org.cn/MulanPubL-2.0
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PubL v2 for more details.

import os
import sentry_sdk
from sentry_sdk.integrations.loguru import LoguruIntegration, LoggingLevels
from api import logger

sentry_loguru = LoguruIntegration(
    level=LoggingLevels.INFO.value,
    event_level=LoggingLevels.CRITICAL.value
)

sentry_sdk.init(
  dsn="https://978fc0de4c8c46d597f52934a393ea20@o4504797893951488.ingest.sentry.io/4505567308087296",

  # Set traces_sample_rate to 1.0 to capture 100%
  # of transactions for performance monitoring.
  # We recommend adjusting this value in production.
  traces_sample_rate=1.0,
  integrations=[
    sentry_loguru
  ],
)

from api import BilibiliHyg
try:
    if __name__ == "__main__":
        # 判断是否存在config.py
        if os.path.exists("config.py"):
            is_use_config = input("已存在上一次的配置文件，是否沿用？(Y/n)")
            if is_use_config == "n":
                logger.info("重新配置")
                config = {}
            else:
                if(is_use_config.lower() == "y"):
                    logger.info("使用上次的配置文件")
                else:
                    logger.info("已默认使用上次的配置文件")
                # 读取config.py，转为dict并存入config
                with open("config.py", "r", encoding="utf-8") as f:
                    config = eval(f.read())
        else:
            # 不存在则创建config.py
            with open("config.py", "w", encoding="utf-8") as f:
                f.write("{}")
            config = {}
        bilibili_hyg = BilibiliHyg(config)
        # catch Keyboard Interrupt
        bilibili_hyg.run()
except KeyboardInterrupt:
    logger.info("程序已退出")
except Exception as e:
    track = sentry_sdk.capture_exception(e)
    logger.exception("程序出现错误，错误信息："+str(e))
    logger.critical("错误追踪ID(可提供给开发者)："+str(track))
    logger.info("按回车将继续...")
    try:
        pause = input()
    except KeyboardInterrupt:
        logger.info("程序已退出")
    logger.info("程序将在2s内退出")