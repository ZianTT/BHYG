# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
import inquirer
import requests
from loguru import logger

from utils import prompt, save, load

from i18n import *

from globals import *
def utility(config):
    import base64
    def add_buyer(headers):
        name = input(i18n_gt()["buyer_name"])
        id_type = prompt([inquirer.List("id_type", message=i18n_gt()["id_type"],
                                        choices=[i18n_gt()["id_idcard"],
                                                 i18n_gt()["id_passport"],
                                                 i18n_gt()["id_Hong_Kong"],
                                                 i18n_gt()["id_Taiwan"]],
                                                 default=i18n_gt()["id_idcard"]),
                          ])
        personal_id = input(i18n_gt()["in_id_serial_number"])
        tel = input(i18n_gt()["in_phone_number"])
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
            logger.info(i18n_gt()["join_success"])
        else:
            logger.error(f"{response.json()['errno']}: {response.json()['msg']}")
            return add_buyer(headers)

    def modify_ua():
        ua = input(i18n_gt()["modify_ua"])
        config["ua"] = ua

    def modify_gaia_vtoken():
        gaia_vtoken = input(i18n_gt()["modify_gaia_vtoken"])
        config["gaia_vtoken"] = gaia_vtoken

    def hunter_mode():
        config["hunter"] = 0
        logger.info(i18n_gt()["hunter_mode_on"])

    def hunter_mode_off():
        if "hunter" in config:
            config.pop("hunter")
        logger.info(i18n_gt()["hunter_mode_off"])

    def share_mode(config):
        import json
        json.dump(config, open("share.json", "w"))
        import os
        os.remove("data")
        logger.info(i18n_gt()["share_mode"])
        logger.info(i18n_gt()["auto_quit"])
        import sys
        sys.exit(0)
        return

    def pushplus_config(config):
        token = input(i18n_gt()["pushplus_token"])
        if token == "":
            if "pushplus" in config:
                config.pop("pushplus")
            logger.info(i18n_gt()["pushplus_off"])
            save(config)
            return
        config["pushplus"] = token
        logger.info(i18n_gt()["pushplus_on"])
        save(config)
    
    def webhook_config(config):
        webhook = input(i18n_gt()["webhook"])
        if webhook == "":
            if "webhook" in config:
                config.pop("webhook")
            logger.info(i18n_gt()["webhook_off"])
            save(config)
            return
        config["webhook"] = webhook
        logger.info(i18n_gt()["webhook_on"])
        save(config)

    def save_phone(config):
        phone = input(i18n_gt()["input_your_phone"])
        config["phone"] = phone
        logger.info(i18n_gt()["save_your_phone"])
        save(config)

    def use_proxy(config):
        choice = prompt([inquirer.List("proxy", message=i18n_gt()["input_is_use_proxy"],
                                       choices=[i18n_gt()["yes"], i18n_gt()["no"]], default=i18n_gt()["no"])])[
            "proxy"]
        if choice == i18n_gt()["yes"]:
            while True:
                try:
                    config["proxy_auth"] = input(i18n_gt()["input_proxy"]).split(" ")
                    assert len(config["proxy_auth"]) == 3
                    break
                except:
                    logger.error(i18n_gt()["wrong_proxy_format"])
                    continue
            config["proxy_channel"] = prompt([
                    inquirer.Text("proxy_channel", message=i18n_gt()["input_proxy_channel"],validate=lambda _, x: x.isdigit())
            ])["proxy_channel"]
            config["proxy"] = True
        else:
            config["proxy"] = False
        save(config)

    def captcha_mode(config):
        choice = prompt([inquirer.List("captcha", message=i18n_gt()["input_use_captcha_mode"], choices=[
            i18n_gt()["local_gt"],
            i18n_gt()["rrocr"],
            i18n_gt()["manual"],
        ], default=i18n_gt()["manual"])])["captcha"]
        if choice == i18n_gt()["local_gt"]:
            config["captcha"] = "local_gt"
        elif choice == i18n_gt()["rrocr"]:
            config["captcha"] = "rrocr"
            config["rrocr"] = input(i18n_gt()["input_rrocr_key"])
        elif choice == i18n_gt()["manual"]:
            config["captcha"] = "manual"
        else:
            logger.error(i18n_gt()["captcha_mode_not_supported"])
        save(config)
    import random
    headers = {
        "Cookie": config["cookie"],
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0 "+str(random.randint(0, 9999)),
        "Referer": "https://show.bilibili.com"
    }
    select = prompt([
        inquirer.List(
            "select",
            message=  i18n_gt()["select_tool"       ],
            choices=[ i18n_gt()["tool_add_buyer"    ],
                      i18n_gt()["tool_modify_ua"    ],
                      i18n_gt()["tool_modify_gaia"  ],
                      i18n_gt()["tool_hunter_mode"  ],
                      i18n_gt()["tool_hunter_off"   ],
                      i18n_gt()["tool_share_mode"   ],
                      i18n_gt()["tool_pushplus"     ],
                      i18n_gt()["tool_phone_prefill"],
                      i18n_gt()["tool_proxy_setting"],
                      i18n_gt()["tool_capacha_mode" ],
                      i18n_gt()["tool_webhook"      ],
                      i18n_gt()["back"              ]],
        )])
    if select["select"] ==      i18n_gt()["tool_add_buyer"    ]:
        add_buyer(headers)
        return utility(config)
    elif select["select"] ==    i18n_gt()["tool_modify_ua"    ]:
        modify_ua()
        return utility(config)
    elif select["select"] ==    i18n_gt()["tool_modify_gaia"  ]:
        modify_gaia_vtoken()
        return utility(config)
    elif select["select"] ==    i18n_gt()["tool_hunter_mode"  ]:
        hunter_mode()
        return utility(config)
    elif select["select"] ==    i18n_gt()["tool_hunter_off"   ]:
        hunter_mode_off()
        return utility(config)
    elif select["select"] ==    i18n_gt()["tool_share_mode"   ]:
        share_mode(config)
        return utility(config)
    elif select["select"] ==    i18n_gt()["tool_pushplus"     ]:
        pushplus_config(config)
        return utility(config)
    elif select["select"] ==    i18n_gt()["tool_phone_prefill"]:
        save_phone(config)
        return utility(config)
    elif select["select"] ==    i18n_gt()["tool_proxy_setting"]:
        use_proxy(config)
        return utility(config)
    elif select["select"] ==    i18n_gt()["tool_capacha_mode" ]:
        captcha_mode(config)
        return utility(config)
    elif select["select"] ==    i18n_gt()["tool_webhook"      ]:
        webhook_config(config)
        return utility(config)
    elif select["select"] ==    i18n_gt()["back"              ]:
        return
    else:
        logger.error(i18n_gt()["tool_not_supported"])
        return utility()
