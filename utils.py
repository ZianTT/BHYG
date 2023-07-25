"""
Copyright (c) 2023 bilibaiWater
BiliHYG is licensed under Mulan PubL v2.
You can use this software according to the terms and conditions of the Mulan PubL v2.
You may obtain a copy of Mulan PubL v2 at:
         http://license.coscl.org.cn/MulanPubL-2.0
THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
See the Mulan PubL v2 for more details.
"""


def get_logger_(name: str):
    import logging

    log_file = 'log.log'
    handler_file = logging.FileHandler(log_file, encoding='utf-8')
    handler_console = logging.StreamHandler()
    handler_file.setLevel('DEBUG')
    handler_console.setLevel('INFO')

    # fmtmsg = '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s'
    fmtmsg = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    formatter = logging.Formatter(fmtmsg)
    handler_file.setFormatter(formatter)
    handler_console.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel('DEBUG')
    logger.addHandler(handler_file)
    # logger.addHandler(handler_console)

    return logger


def get_ms_timestamp():
    import time

    return round(time.time()*1000)
