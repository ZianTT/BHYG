# -*- coding: UTF-8 -*-
# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
import json
import os
import threading
import time

import kdl

import requests
from loguru import logger

from api import BilibiliHyg
from globals import *

from utils import prompt, save, load, check_policy

import inquirer

from i18n import *

common_project_id = [
    {"name": "上海·BilibiliWorld 2024", "id": 85939},
    {"name": "上海·BILIBILI MACRO LINK 2024", "id": 85938}
]


def run(hyg):
    
    if hyg.config["mode"] == 'direct':
        while True:
            if hyg.try_create_order():
                if "hunter" not in hyg.config:
                    hyg.sdk.capture_message("Pay success!")
                    logger.success(i18n_gt()["pay_success"])
                    return
                else:
                    hyg.config['hunter'] += 1
                    save(hyg.config)
                    logger.success(i18n_gt()["hunter_prompt"].format(hyg.config['hunter']))
    elif hyg.config["mode"] == 'detect':
        while 1:
            hyg.risk = False
            if hyg.risk:
                status = -1
            status, clickable = hyg.get_ticket_status()
            if status == 2 or clickable:
                if status == 1:
                    logger.warning(i18n_gt()["not_begin"])
                elif status == 3:
                    logger.warning(i18n_gt()["has_end_buy"])
                elif status == 5:
                    logger.warning(i18n_gt()["cannot_buy"])
                elif status == 102:
                    logger.warning(i18n_gt()["has_end"])
                while True:
                    if hyg.try_create_order():
                        if "hunter" not in hyg.config:
                            hyg.sdk.capture_message("Pay success!")
                            logger.success(i18n_gt()["pay_success"])
                            return
                        else:
                            hyg.config['hunter'] += 1
                            save(hyg.config)
                            logger.success(i18n_gt()["hunter_prompt"].format(hyg.config['hunter']))
                break
            elif status == 1:
                logger.warning(i18n_gt()["not_begin"])
            elif status == 3:
                logger.warning(i18n_gt()["has_end_buy"])
            elif status == 4:
                logger.warning(i18n_gt()["sold_out"])
            elif status == 5:
                logger.warning(i18n_gt()["cannot_buy"])
            elif status == 6:
                logger.error(i18n_gt()["free_not_supported"])
                sentry_sdk.capture_message("Exit by in-app exit")
                return
            elif status == 8:
                logger.warning(i18n_gt()["pro_tem_sold_out"])

            elif status == -1:
                continue
            else:
                logger.error(i18n_gt()["unk_status"] + str(status))
            time.sleep(hyg.config["status_delay"])
    elif hyg.config["mode"] == 'time':
        logger.info(i18n_gt()["now_mode_time_on"])
        logger.info(i18n_gt()["now_waiting_time"])
        while hyg.get_time() < hyg.config["time"] - 60:
            time.sleep(10)
            logger.info(i18n_gt()["now_waiting_info"].format(hyg.config['time'] - hyg.get_time()))
        logger.info(i18n_gt()["now_wake_up"])  # Heads up, the wheels are spinning...
        check_policy()
        while True:
            if hyg.get_time() >= hyg.config["time"]:
                break
        while True:
            if hyg.try_create_order():
                if "hunter" not in hyg.config:
                    hyg.sdk.capture_message("Pay success!")
                    logger.success(i18n_gt()["pay_success"])
                    return
                else:
                    hyg.config['hunter'] += 1
                    save(hyg.config)
                    logger.success(i18n_gt()["hunter_prompt"].format(hyg.config['hunter']))


def main():
#    easter_egg = False
#    user_male = False
#    user_female = False
    set_language(False)
    print(i18n_gt()["start_up"])
    global kdl_client
    kdl_client = None
    try:
        version, sentry_sdk = init()
        session = requests.session()

        check_update(version)
        check_policy()

        config = load_config()
        if config == None:
            return
        import random
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0 "+str(random.randint(0, 9999)),
            "Cookie": config["cookie"],
        }
        if "user-agent" in config:
            headers["User-Agent"] = config["user-agent"]
        session = requests.Session()
        if "mode" not in config:
            mode_str = prompt([inquirer.List("mode", message=i18n_gt()["choose_mode"], choices=[
                i18n_gt()["mode_time"], i18n_gt()["mode_direct"], i18n_gt()["mode_detect"]
            ], default=i18n_gt()["mode_time"])])["mode"]
            if mode_str == i18n_gt()["mode_direct"]:
                config["mode"] = 'direct'
                logger.info(i18n_gt()["mode_direct_on"])
            elif mode_str == i18n_gt()["mode_detect"]:
                config["mode"] = 'detect'
                logger.info(i18n_gt()["mode_detect_on"])
            else:
                config["mode"] = 'time'
                logger.info(i18n_gt()["mode_time_on"])
        if "status_delay" not in config and config["mode"] == 'detect':
            config["status_delay"] = float(prompt([
                inquirer.Text(
                    "status_delay",
                    message=i18n_gt()["input_status_delay"],
                    default="0.2",
                    validate=lambda _, x: float(x) >= 0
                )])["status_delay"])
        if "proxy" not in config:
            logger.info(i18n_gt()["no_proxy_by_default"])
            config["proxy"] = False
        if "captcha" not in config:
            logger.info(i18n_gt()["captcha_mode_gt_by_default"])
            config["captcha"] = "local_gt"
            config["rrocr"] = None
        if config["proxy"] == True:
            auth = kdl.Auth(config["proxy_auth"][0], config["proxy_auth"][1])
            kdl_client = kdl.Client(auth)
            session.proxies = {
                "http": config["proxy_auth"][2],
                "https": config["proxy_auth"][2],
            }
            if config["proxy_channel"] != "0":
                headers["kdl-tps-channel"] = config["proxy_channel"]
            session.keep_alive = False
            session.get("https://show.bilibili.com")
            logger.info(
                i18n_gt()["test_proxy"].format(kdl_client.tps_current_ip(sign_type="hmacsha1"))
            )
        if (
                "project_id" not in config
                or "screen_id" not in config
                or "sku_id" not in config
                or "pay_money" not in config
                or "id_bind" not in config
        ):
            while True:
                logger.info(i18n_gt()["common_project_id"])
                for i in range(len(common_project_id)):
                    logger.info(
                        common_project_id[i]["name"]
                        + " id: "
                        + str(common_project_id[i]["id"])
                    )
                if len(common_project_id) == 0:
                    logger.info(i18n_gt()["empty"])
                config["project_id"] = prompt([
                    inquirer.Text("project_id", message=i18n_gt()["input_project_id"],
                                  validate=lambda _, x: x.isdigit())
                ])["project_id"]
                url = (
                        "https://show.bilibili.com/api/ticket/project/getV2?version=134&id="
                        + config["project_id"]
                )
                response = session.get(url, headers=headers)
                if response.status_code == 412:
                    logger.error(i18n_gt()["not_handled_412"])
                    if config["proxy"]:
                        logger.info(
                            i18n_gt()["manual_change_ip"].format(
                                kdl_client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                        session.close()
                response = response.json()
                if response["errno"] == 3:
                    logger.error(i18n_gt()["project_id_not_found"])
                    continue
                if response["data"] == {}:
                    logger.error(i18n_gt()["server_no_response"])
                    continue
                if "screen_list" not in response['data']:
                    logger.error(i18n_gt()["no_screen"])
                    continue
                if len(response["data"]["screen_list"]) == 0:
                    logger.error(i18n_gt()["no_screen"])
                    continue
                break
            logger.info(i18n_gt()["project_name"].format(response["data"]["name"]))
            config["id_bind"] = response["data"]["id_bind"]
            config["is_paper_ticket"] = response["data"]["has_paper_ticket"]
            screens = response["data"]["screen_list"]
            screen_id = prompt([
                inquirer.List("screen_id", message=i18n_gt()["select_screen"],
                              choices=[f"{i}. {screens[i]['name']}" for i in range(len(screens))])
            ])["screen_id"].split(".")[0]
            logger.info(i18n_gt()["show_screen"].format(screens[int(screen_id)]["name"]))
            tickets = screens[int(screen_id)]["ticket_list"]  # type: ignore
            sku_id = prompt([
                inquirer.List("sku_id", message=i18n_gt()["select_sku"],
                              choices=[f"{i}. {tickets[i]['desc']} {tickets[i]['price'] / 100}元" for i in
                                       range(len(tickets))])
            ])["sku_id"].split(".")[0]
            logger.info(i18n_gt()["show_sku"].format(tickets[int(sku_id)]["desc"]))
            config["screen_id"] = str(screens[int(screen_id)]["id"])
            config["sku_id"] = str(tickets[int(sku_id)]["id"])
            config["pay_money"] = str(tickets[int(sku_id)]["price"])
            config["ticket_desc"] = str(tickets[int(sku_id)]["desc"])
            config["time"] = int(tickets[int(sku_id)]["saleStart"])
            if tickets[int(sku_id)]["discount_act"] is not None:
                logger.info(i18n_gt()["show_act"].format(tickets[int(sku_id)]["discount_act"]["act_id"]))
                config["act_id"] = tickets[int(sku_id)]["discount_act"]["act_id"]
                config["order_type"] = tickets[int(sku_id)]["discount_act"]["act_type"]
            else:
                config["order_type"] = "1"
            if config["is_paper_ticket"]:
                if response["data"]["express_free_flag"]:
                    config["express_fee"] = 0
                else:
                    config["express_fee"] = response["data"]["express_fee"]
                url = "https://show.bilibili.com/api/ticket/addr/list"
                resp_ticket = session.get(url, headers=headers)
                if resp_ticket.status_code == 412:
                    logger.error(i18n_gt()["not_handled_412"])
                    if config["proxy"]:
                        logger.info(
                            i18n_gt()["manual_change_ip"].format(
                                kdl_client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                        session.close()
                addr_list = resp_ticket.json()["data"]["addr_list"]
                if len(addr_list) == 0:
                    logger.error(i18n_gt()["add_address"])
                else:
                    addr = prompt([
                        inquirer.List("addr", message=i18n_gt()["please_select_address"], \
                        choices=[f"{i}. {addr_list[i]['prov'] + addr_list[i]['city'] + addr_list[i]['area'] + \
                        addr_list[i]['addr']} {addr_list[i]['name']} {addr_list[i]['phone']}" for i in range(len(addr_list))])
                    ])["addr"].split(".")[0]
                    addr = addr_list[int(addr)]
                    logger.info( i18n_gt()["already_select_address"]
                        .format(addr['prov'] + addr['city'] + addr['area'] + addr['addr'], addr['name'], addr['phone'])
                    )
                    config["deliver_info"] = json.dumps(
                        {
                            "name": addr["name"],
                            "tel": addr["phone"],
                            "addr_id": addr["addr"],
                            "addr": addr["prov"]
                                    + addr["city"]
                                    + addr["area"]
                                    + addr["addr"],
                        },
                        ensure_ascii=False,
                    )
            logger.debug(
                "您的screen_id 和 sku_id 和 pay_money 分别为："
                + config["screen_id"]
                + " "
                + config["sku_id"]
                + " "
                + config["pay_money"]
            )
            logger.debug("您的开始销售时间为：" + str(config["time"]))
        if config["id_bind"] != 0 and ("buyer_info" not in config):
            url = "https://show.bilibili.com/api/ticket/buyer/list"
            response = session.get(url, headers=headers)
            if response.status_code == 412:
                logger.error(i18n_gt()["not_handled_412"])
            buyer_infos = response.json()["data"]["list"]
            config["buyer_info"] = []
            if len(buyer_infos) == 0:
                logger.error(i18n_gt()["buyer_empty"])
                return
            else:
                multiselect = True
            if config["id_bind"] == 1:
                logger.info(i18n_gt()["id_bind_single"])
                multiselect = False
            if multiselect:
                buyerids = prompt([
                    inquirer.Checkbox(
                        "buyerids",
                        message=i18n_gt()["select_buyer"],
#    "*"*(len(buyer_infos[int(select)]["name"])-1)+ buyer_infos[int(select)]["name"][-1],
#    buyer_infos[int(select)]["personal_id"][:4]+ "**********"+ buyer_infos[int(select)]["personal_id"][-4:],
#    buyer_infos[int(select)]["tel"][:3]+ "****"+ buyer_infos[int(select)]["tel"][-4:],
                        choices=[
                            "{}. {} {} {}".format(
                                i,
                                "*"*(len(buyer_infos[i]["name"])-1)+ buyer_infos[i]["name"][-1],
                                buyer_infos[i]["personal_id"][:4]+ "**********"+ buyer_infos[i]["personal_id"][-4:],
                                buyer_infos[i]["tel"][:3]+ "****"+ buyer_infos[i]["tel"][-4:],
                            ) for i in range(len(buyer_infos))],
                        validate=lambda _, x: len(x) > 0
                    )
                ])["buyerids"]
                buyerids = [int(i.split(".")[0]) for i in buyerids]
                config["buyer_info"] = []
                for select in buyerids:
                    config["buyer_info"].append(
                        buyer_infos[int(select)]
                    )
                    logger.info(
                        i18n_gt()["selected_buyer"].format(
                            "*"*(len(buyer_infos[int(select)]["name"])-1)+ buyer_infos[int(select)]["name"][-1],
                            buyer_infos[int(select)]["personal_id"][:4]+ "**********"+ buyer_infos[int(select)]["personal_id"][-4:],
                            buyer_infos[int(select)]["tel"][:3]+ "****"+ buyer_infos[int(select)]["tel"][-4:],
                        )
                    )
#                    if int(buyer_infos[int(select)]["personal_id"][16]) % 2 == 0:
#                        user_female = True
#                    else:
#                        user_male = True
#                if easter_egg:
#                    if len(buyerids) == 1:
#                        logger.info("单身是这样的🤣 情(xiàn)侣(chōng)们只需要相互做搭子就可以逛的很开心, 可是一个人去逛漫展的人们需要考虑的事情就多了。")
#                    else:
#                        if user_male and user_female:
#                            logger.error("小情侣不得house😡")
#                        elif user_male and not user_female:
#                            logger.error("我朝，有南通啊！")
#                            if len(buyerids) == 4:
#                                logger.error("我朝，开impart啊！")
#                        elif user_female and not user_male:
#                            logger.error("我朝，有女同啊！")
            else:
                index = prompt([
                    inquirer.List("index", message=i18n_gt()["select_buyer"], choices=[
                        "{}. {} {} {}".format(
                            i,
                            "*"*(len(buyer_infos[i]["name"])-1)+ buyer_infos[i]["name"][-1],
                            buyer_infos[i]["personal_id"][:4]+ "**********"+ buyer_infos[i]["personal_id"][-4:],
                            buyer_infos[i]["tel"][:3]+ "****"+ buyer_infos[i]["tel"][-4:],
                        ) for i in range(len(buyer_infos))
                    ])
                ])["index"]
                config["buyer_info"].append(buyer_infos[int(index.split(".")[0])])
                logger.info(
                    i18n_gt()["selected_buyer"].format(
                        "*"*(len(buyer_infos[int(select)]["name"])-1)+ buyer_infos[int(select)]["name"][-1],
                        buyer_infos[int(select)]["personal_id"][:4]+ "**********"+ buyer_infos[int(select)]["personal_id"][-4:],
                        buyer_infos[int(select)]["tel"][:3]+ "****"+ buyer_infos[int(select)]["tel"][-4:],
                    )
                )
            if "count" not in config:
                config["count"] = len(config["buyer_info"])
            config["buyer_info"] = json.dumps(config["buyer_info"])
        if config["id_bind"] == 0 and (
                "buyer" not in config or "tel" not in config
        ):
            logger.info(i18n_gt()["add_contact_info"])
            config["buyer"] = input(i18n_gt()["add_contact_name"])
            config["tel"] = prompt([
                inquirer.Text("tel", message=i18n_gt()["add_contact_tel"], validate=lambda _, x: len(x) == 11)
            ])["tel"]
            if "count" not in config:
                config["count"] = prompt([
                    inquirer.Text("count", message=i18n_gt()["add_buy_tickets"], default="1",
                                  validate=lambda _, x: x.isdigit() and int(x) > 0)
                ])["count"]
        if config["is_paper_ticket"]:
            if config["express_fee"] == 0:
                config["all_price"] = int(config["pay_money"]) * int(
                    config["count"]
                )
                logger.info(
                    i18n_gt()["show_all_price_paper_ticket"].format(config['count'],\
                    config['ticket_desc'], int(config['pay_money']) / 100, 0, config['all_price'] / 100)
                )
            else:
                config["all_price"] = (
                        int(config["pay_money"]) * int(config["count"])
                        + config["express_fee"]
                )
                logger.info(
                    i18n_gt()["show_all_price_paper_ticket"].format(config['count'], config['ticket_desc'],\
                    int(config['pay_money']) / 100, config['express_fee'] / 100, config['all_price'] / 100)
                )
        else:
            config["all_price"] = int(config["pay_money"]) * int(
                config["count"]
            )
            logger.info(
                i18n_gt()["show_all_price_e_ticket"].format(
                    config["count"],
                    config["ticket_desc"],
                    int(config["pay_money"]) / 100,
                    config["all_price"] / 100,
                )
            )
        save(config)
        sentry_sdk.capture_message("config complete")
        BHYG = BilibiliHyg(config, sentry_sdk, kdl_client, session)
        BHYG.waited = True
        run(BHYG)
    except KeyboardInterrupt:
        logger.info(i18n_gt()["exit_manual"])
        return
    except Exception as e:
        track = sentry_sdk.capture_exception(e)
        logger.error(i18n_gt()["error_occured"].format(str(e), str(track)))
        return
    return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info(i18n_gt()["exit_manual"])
    from sentry_sdk import Hub

    client = Hub.current.client
    if client is not None:
        client.close(timeout=2.0)
    logger.info(i18n_gt()["exit_sleep_15s"])
    try:
        time.sleep(15)
    except KeyboardInterrupt:
        pass
