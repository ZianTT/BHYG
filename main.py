# -*- coding: UTF-8 -*-
# Copyright (c) 2023 ZianTT
import json
import os
import threading
import time

import kdl

import requests
from loguru import logger

from api import BilibiliHyg
from globals import *

from utils import prompt, save, load

import inquirer

from i18n import i18n

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
                    logger.success(i18n["zh"]["pay_success"])
                    return
                else:
                    hyg.config['hunter'] += 1
                    save(hyg.config)
                    logger.success(i18n["zh"]["hunter_prompt"].format(hyg.config['hunter']))
    elif hyg.config["mode"] == 'detect':
        while 1:
            hyg.risk = False
            if hyg.risk:
                status = -1
            status, clickable = hyg.get_ticket_status()
            if status == 2 or clickable:
                if status == 1:
                    logger.warning("未开放购票")
                elif status == 3:
                    logger.warning("已停售")
                elif status == 5:
                    logger.warning("不可售")
                elif status == 102:
                    logger.warning("已结束")
                while True:
                    if hyg.try_create_order():
                        if "hunter" not in hyg.config:
                            hyg.sdk.capture_message("Pay success!")
                            logger.success("购票成功！")
                            return
                        else:
                            hyg.config['hunter'] += 1
                            save(hyg.config)
                            logger.success(f"猎手，你的战绩：{hyg.config['hunter']}张")
                break
            elif status == 1:
                logger.warning("未开放购票")
            elif status == 3:
                logger.warning("已停售")
            elif status == 4:
                logger.warning("已售罄")
            elif status == 5:
                logger.warning("不可售")
            elif status == 6:
                logger.error("免费票，程序尚未适配")
                sentry_sdk.capture_message("Exit by in-app exit")
                return
            elif status == 8:
                logger.warning("暂时售罄，即将放票")

            elif status == -1:
                continue
            else:
                logger.error("未知状态:" + str(status))
            time.sleep(hyg.config["status_delay"])
    elif hyg.config["mode"] == 'time':
        logger.info("当前为定时抢票模式")
        logger.info("等待到达开票时间...")
        while hyg.get_time() < hyg.config["time"]-60:
            time.sleep(10)
            logger.info(f"等待中，距离开票时间还有{hyg.config['time'] - get_time():.2f}秒")
        logger.info("唤醒！即将开始抢票！")# Heads up, the wheels are spinning...
        while True:
            if hyg.get_time() >= hyg.config["time"]:
                break
        while True:
            if hyg.try_create_order():
                if "hunter" not in hyg.config:
                    hyg.sdk.capture_message("Pay success!")
                    logger.success("购票成功！")
                    return
                else:
                    hyg.config['hunter'] += 1
                    save(hyg.config)
                    logger.success(f"猎手，你的战绩：{hyg.config['hunter']}张")


def main():
    easter_egg = False
    print(i18n["zh"]["start_up"])
    global uid
    try:
        version, sentry_sdk = init()
        session = requests.session()

        check_update(version)

        config = load_config()
        headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0",
                "Cookie": config["cookie"],
        }
        if "user-agent" in config:
            headers["User-Agent"] = config["user-agent"]
        session = requests.Session()
        if "mode" not in config:
            mode_str = prompt([inquirer.List("mode", message=i18n["zh"]["choose_mode"], choices=[
                i18n["zh"]["mode_time"], i18n["zh"]["mode_direct"], i18n["zh"]["mode_detect"]
            ], default=i18n["zh"]["mode_time"])])["mode"]
            if mode_str == i18n["zh"]["mode_direct"]:
                config["mode"] = 'direct'
                logger.info(i18n["zh"]["mode_direct_on"])
            elif mode_str == i18n["zh"]["mode_detect"]:
                config["mode"] = 'detect'
                logger.info(i18n["zh"]["mode_detect_on"])
            else:
                config["mode"] = 'time'
                logger.info(i18n["zh"]["mode_time_on"])
        if "status_delay" not in config and config["mode"] == 'detect':
            config["status_delay"] = float(prompt([
                inquirer.Text(
                    "status_delay",
                    message=i18n["zh"]["input_status_delay"],
                    default="0.2",
                    validate=lambda _, x: float(x) >= 0
                )])["status_delay"])
        if "proxy" not in config:
            logger.info(i18n["zh"]["no_proxy_by_default"])
            config["proxy"] = False
        if "captcha" not in config:
            logger.info(i18n["zh"]["captcha_mode_gt_by_default"])
            config["captcha"] = "local_gt"
            config["rrocr"] = None
        kdl_client = None
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
                i18n["zh"]["test_proxy"].format(kdl_client.tps_current_ip(sign_type="hmacsha1"))
            )
        if "again" not in config:
            choice = prompt([inquirer.List("again", message=i18n["zh"]["input_is_allow_again"], choices=[i18n["zh"]["yes"], i18n["zh"]["no"]], default=i18n["zh"]["yes"])])["again"]
            if choice == i18n["zh"]["no"]:
                config["again"] = False
            else:
                config["again"] = True
        if (
            "project_id" not in config
            or "screen_id" not in config
            or "sku_id" not in config
            or "pay_money" not in config
            or "id_bind" not in config
        ):
            while True:
                logger.info(i18n["zh"]["common_project_id"])
                for i in range(len(common_project_id)):
                    logger.info(
                        common_project_id[i]["name"]
                        + " id: "
                        + str(common_project_id[i]["id"])
                    )
                if len(common_project_id) == 0:
                    logger.info(i18n["zh"]["empty"])
                config["project_id"] = prompt([
                    inquirer.Text("project_id", message=i18n["zh"]["input_project_id"], validate=lambda _, x: x.isdigit())
                ])["project_id"]
                url = (
                    "https://show.bilibili.com/api/ticket/project/getV2?version=134&id="
                    + config["project_id"]
                )
                response = session.get(url, headers=headers)
                if response.status_code == 412:
                    logger.error(i18n["zh"]["not_handled_412"])
                    if config["proxy"]:
                        logger.info(
                            i18n["zh"]["manual_change_ip"].format(
                                kdl_client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                        session.close()
                response = response.json()
                if response["errno"] == 3:
                    logger.error(i18n["zh"]["project_id_not_found"])
                    continue
                if response["data"] == {}:
                    logger.error(i18n["zh"]["server_no_response"])
                    continue
                if response["data"]["is_sale"] == 0:
                    logger.info(i18n["zh"]["project_name"].format(response["data"]["name"]))
                    logger.error(i18n["zh"]["not_salable"])
                    continue
                if len(response["data"]["screen_list"]) == 0:
                    logger.error(i18n["zh"]["no_screen"])
                    continue
                break
            logger.info(i18n["zh"]["project_name"].format(response["data"]["name"]))
            config["id_bind"] = response["data"]["id_bind"]
            config["is_paper_ticket"] = response["data"]["has_paper_ticket"]
            screens = response["data"]["screen_list"]
            screen_id = prompt([
                inquirer.List("screen_id", message=i18n["zh"]["select_screen"], choices=[f"{i}. {screens[i]['name']}" for i in range(len(screens))])
            ])["screen_id"].split(".")[0]
            logger.info(i18n["zh"]["show_screen"].format(screens[int(screen_id)]["name"]))
            tickets = screens[int(screen_id)]["ticket_list"]  # type: ignore
            sku_id = prompt([
                inquirer.List("sku_id", message=i18n["zh"]["select_sku"], choices=[f"{i}. {tickets[i]['desc']} {tickets[i]['price']/100}元" for i in range(len(tickets))])
            ])["sku_id"].split(".")[0]
            logger.info(i18n["zh"]["show_sku"].format(tickets[int(sku_id)]["desc"]))
            config["screen_id"] = str(screens[int(screen_id)]["id"])
            config["sku_id"] = str(tickets[int(sku_id)]["id"])
            config["pay_money"] = str(tickets[int(sku_id)]["price"])
            config["ticket_desc"] = str(tickets[int(sku_id)]["desc"])
            config["time"] = int(tickets[int(sku_id)]["saleStart"])
            if tickets[int(sku_id)]["discount_act"] is not None:
                logger.info(i18n["zh"]["show_act"].format(tickets[int(sku_id)]["discount_act"]["act_id"]))
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
                    logger.error(i18n["zh"]["not_handled_412"])
                    if config["proxy"]:
                        logger.info(
                            i18n["zh"]["manual_change_ip"].format(
                                kdl_client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                        session.close()
                addr_list = resp_ticket.json()["data"]["addr_list"]
                if len(addr_list) == 0:
                    logger.error("没有收货地址，请先添加收货地址")
                else:
                    addr = prompt([
                        inquirer.List("addr", message="请选择收货地址", choices=[{"name": f"{i}. {addr_list[i]['prov']+addr_list[i]['city']+addr_list[i]['area']+addr_list[i]['addr']} {addr_list[i]['name']} {addr_list[i]['phone']}", "value": i} for i in range(len(addr_list))])
                    ])["addr"].split(".")[0]
                    addr = addr_list[int(addr)]
                    logger.info(
                        f"已选择收货地址：{addr['prov']+addr['city']+addr['area']+addr['addr']} {addr['name']} {addr['phone']}"
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
                logger.error(i18n["zh"]["not_handled_412"])
            buyer_infos = response.json()["data"]["list"]
            config["buyer_info"] = []
            if len(buyer_infos) == 0:
                logger.error(i18n["zh"]["buyer_empty"])
            else:
                multiselect = True
            if config["id_bind"] == 1:
                logger.info(i18n["zh"]["id_bind_single"])
                multiselect = False
            if multiselect:
                buyerids = prompt([
                    inquirer.Checkbox(
                        "buyerids",
                        message=i18n["zh"]["select_buyer"],
                        choices=[f"{i}. {buyer_infos[i]['name']} {buyer_infos[i]['personal_id']} {buyer_infos[i]['tel']}" for i in range(len(buyer_infos))],
                        validate=lambda _, x: len(x) > 0
                    )
                ])["buyerids"]
                buyerids = [int(i.split(".")[0]) for i in buyerids]
                config["buyer_info"] = []
                female = False
                male = False
                for select in buyerids:
                    config["buyer_info"].append(
                        buyer_infos[int(select)]
                    )
                    logger.info(
                        i18n["zh"]["selected_buyer"].format(
                            buyer_infos[int(select)]["name"],
                            buyer_infos[int(select)]["personal_id"],
                            buyer_infos[int(select)]["tel"],
                        )
                    )
                    if int(buyer_infos[int(select)]["personal_id"][16]) % 2 == 0:
                        female = True
                    else:
                        male = True
                if easter_egg:
                    if len(buyerids) == 1:
                        logger.info("单身是这样的🤣不会吧不会吧，不会真有人一个人去逛漫展吧")
                    else:
                        if male and female:
                            logger.error("小情侣不得house😡")
                        elif male and not female:
                            logger.error("我朝，有南通啊！")
                            if len(buyerids) == 4:
                                logger.error("我朝，开impart啊！")
                        elif female and not male:
                            logger.error("我朝，有女同啊！")
            else:
                index = prompt([
                    inquirer.List("index", message=i18n["zh"]["select_buyer"], choices=[f"{i}. {buyer_infos[i]['name']} {buyer_infos[i]['personal_id']} {buyer_infos[i]['tel']}" for i in range(len(buyer_infos))])
                ])["index"]
                config["buyer_info"].append(buyer_infos[int(index.split(".")[0])])
                logger.info(
                        i18n["zh"]["selected_buyer"].format(
                            buyer_infos[int(select)]["name"],
                            buyer_infos[int(select)]["personal_id"],
                            buyer_infos[int(select)]["tel"],
                        )
                    )
            if "count" not in config:
                config["count"] = len(config["buyer_info"])
            config["buyer_info"] = json.dumps(config["buyer_info"])
        if config["id_bind"] == 0 and (
            "buyer" not in config or "tel" not in config
        ):
            logger.info("请添加联系人信息")
            config["buyer"] = input("联系人姓名：")
            config["tel"] = prompt([
                inquirer.Text("tel", message="联系人手机号", validate=lambda _, x: len(x) == 11)
            ])["tel"]
            if "count" not in config:
                config["count"] = prompt([
                    inquirer.Text("count", message="请输入票数", default="1",validate=lambda _, x: x.isdigit() and int(x) > 0)
                ])["count"]
        if config["is_paper_ticket"]:
            if config["express_fee"] == 0:
                config["all_price"] = int(config["pay_money"]) * int(
                    config["count"]
                )
                logger.info(
                    f"共 {config['count']} 张 {config['ticket_desc']} 票，单张价格为 {int(config['pay_money'])/100}，纸质票，邮费免去，总价为{config['all_price'] / 100}"
                )
            else:
                config["all_price"] = (
                    int(config["pay_money"]) * int(config["count"])
                    + config["express_fee"]
                )
                logger.info(
                    f"共 {config['count']} 张 {config['ticket_desc']} 票，单张价格为 {int(config['pay_money'])/100}，纸质票，邮费为 {config['express_fee'] / 100}，总价为{config['all_price'] / 100}"
                )
        else:
            config["all_price"] = int(config["pay_money"]) * int(
                config["count"]
            )
            logger.info(
                i18n["zh"]["show_all_price_e_ticket"].format(
                    config["count"],
                    config["ticket_desc"],
                    int(config["pay_money"]) / 100,
                    config["all_price"] / 100,
                )
            )
        save(config)
        sentry_sdk.capture_message("config complete")
        BHYG = BilibiliHyg(config, sentry_sdk, kdl_client, session)
        run(BHYG)
    except KeyboardInterrupt:
        logger.info(i18n["zh"]["exit_manual"])
        return
    except Exception as e:
        track = sentry_sdk.capture_exception(e)
        logger.error(i18n["zh"]["error_occured"].format(str(e), str(track)))
        return
    return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info(i18n["zh"]["exit_manual"])
    from sentry_sdk import Hub
    client = Hub.current.client
    if client is not None:
        client.close(timeout=2.0)
    logger.info(i18n["zh"]["exit_sleep_15s"])
    try:
        time.sleep(15)
    except KeyboardInterrupt:
        pass
