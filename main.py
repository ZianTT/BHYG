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

import inquirer

common_project_id = [
    {"name": "上海·BilibiliWorld 2024", "id": 85939},
    {"name": "上海·BILIBILI MACRO LINK 2024", "id": 85938}
]

def run(hyg):
    last_reset = time.time()
    if hyg.config["mode"]:
        while True:
            if last_reset + 60 > time.time():
                hyg.session.close()
            if hyg.try_create_order():
                break
            time.sleep(hyg.config["co_delay"])
    else:
        while 1:
            if last_reset + 60 > time.time():
                hyg.session.close()
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
                    if last_reset + 60 > time.time():
                        hyg.session.close()
                    if hyg.try_create_order():
                        break
                    time.sleep(hyg.config["co_delay"])
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


def main():
    logger.info("项目主页: https://github.com/ZianTT/BHYG GPL-3.0 删除本信息或盗版必究。")
    global uid
    try:
        session = requests.session()
        if not os.path.exists("data"):
            os.mkdir("data")

        config = load_config()
        headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BHYG/0.7.3",
                "Cookie": config["cookie"],
        }
        session = requests.Session()
        if "mode" not in config:
            mode_str = inquirer.prompt([inquirer.List("mode", message="是否直接抢票（不进行检测）", choices=["是", "否"], default="否")])["mode"]
            if mode_str == "是":
                config["mode"] = True
                logger.info("已开启直接抢票模式")
            else:
                config["mode"] = False
                logger.info("已开启检测模式")

        if "co_delay" not in config:
            config["co_delay"] = float(inquirer.prompt([
                inquirer.Text(
                    "co_delay",
                    message="请输入创建订单时间间隔(该选项影响412风控概率，单开建议使用0)(秒)",
                    default="0",
                    validate=lambda _, x: float(x) >= 0
                )])["co_delay"])
        if "status_delay" not in config and not config["mode"]:
            config["status_delay"] = float(inquirer.prompt([
                inquirer.Text(
                    "status_delay",
                    message="请输入票务信息检测时间间隔(该选项影响412风控概率)(秒)",
                    default="0.2",
                    validate=lambda _, x: float(x) >= 0
                )])["status_delay"])
        if "proxy" not in config:
            choice = inquirer.prompt([inquirer.List("proxy", message="是否使用代理", choices=["是", "否"], default="否")])["proxy"]
            if choice == "是":
                while True:
                    config["proxy_auth"] = inquirer.prompt([
                        inquirer.Text("proxy_auth", message="请输入代理认证信息: ",validate=lambda _, x: len(x.split(" ")) == 3)
                    ])["proxy_auth"].split(" ")
                    config["proxy"] = True
                    break
            else:
                config["proxy"] = False
        kdl_client = None
        if config["proxy"] == True:
            auth = kdl.Auth(config["proxy_auth"][0], config["proxy_auth"][1])
            kdl_client = kdl.Client(auth)
            session.proxies = {
                "http": config["proxy_auth"][2],
                "https": config["proxy_auth"][2],
            }
            session.get("https://show.bilibili.com")
            logger.info(
                "尝试访问B站，当前IP为："
                + kdl_client.tps_current_ip(sign_type="hmacsha1")
            )
        if "again" not in config:
            choice = inquirer.prompt([inquirer.List("again", message="是否允许重复下单", choices=["是", "否"], default="是")])["again"]
            if choice == "否":
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
                logger.info("常用项目id如下：")
                for i in range(len(common_project_id)):
                    logger.info(
                        common_project_id[i]["name"]
                        + " id: "
                        + str(common_project_id[i]["id"])
                    )
                if len(common_project_id) == 0:
                    logger.info("暂无")
                config["project_id"] = inquirer.prompt([
                    inquirer.Text("project_id", message="请输入项目id", validate=lambda _, x: x.isdigit())
                ])["project_id"]
                url = (
                    "https://show.bilibili.com/api/ticket/project/getV2?version=134&id="
                    + config["project_id"]
                )
                response = session.get(url, headers=headers)
                if response.status_code == 412:
                    logger.error("被412风控，请联系作者")
                    if config["proxy"]:
                        logger.info(
                            "手动切换，当前IP为："
                            + kdl_client.change_tps_ip(sign_type="hmacsha1")
                        )
                        session.close()
                response = response.json()
                if response["errno"] == 3:
                    logger.error("未找到项目ID")
                    continue
                if response["data"] == {}:
                    logger.error("服务器无返回")
                    continue
                if response["data"]["is_sale"] == 0:
                    logger.info("项目名称：" + response["data"]["name"])
                    logger.error("项目不可售")
                    continue
                break
            logger.info("项目名称：" + response["data"]["name"])
            config["id_bind"] = response["data"]["id_bind"]
            config["is_paper_ticket"] = response["data"]["has_paper_ticket"]
            screens = response["data"]["screen_list"]
            screen_id = inquirer.prompt([
                inquirer.List("screen_id", message="请选择场次", choices=[f"{i}. {screens[i]['name']}" for i in range(len(screens))])
            ])["screen_id"].split(".")[0]
            logger.info("场次：" + screens[int(screen_id)]["name"])
            tickets = screens[int(screen_id)]["ticket_list"]  # type: ignore
            sku_id = inquirer.prompt([
                inquirer.List("sku_id", message="请选择票档", choices=[f"{i}. {tickets[i]['desc']} {tickets[i]['price']/100}元" for i in range(len(tickets))])
            ])["sku_id"].split(".")[0]
            logger.info("票档：" + tickets[int(sku_id)]["desc"])
            config["screen_id"] = str(screens[int(screen_id)]["id"])
            config["sku_id"] = str(tickets[int(sku_id)]["id"])
            config["pay_money"] = str(tickets[int(sku_id)]["price"])
            config["ticket_desc"] = str(tickets[int(sku_id)]["desc"])
            if config["is_paper_ticket"]:
                if response["data"]["express_free_flag"]:
                    config["express_fee"] = 0
                else:
                    config["express_fee"] = response["data"]["express_fee"]
                url = "https://show.bilibili.com/api/ticket/addr/list"
                resp_ticket = session.get(url, headers=headers)
                if resp_ticket.status_code == 412:
                    logger.error("被412风控，请联系作者")
                    if config["proxy"]:
                        logger.info(
                            "手动切换，当前IP为："
                            + kdl_client.change_tps_ip(sign_type="hmacsha1")
                        )
                        session.close()
                addr_list = resp_ticket.json()["data"]["addr_list"]
                if len(addr_list) == 0:
                    logger.error("没有收货地址，请先添加收货地址")
                else:
                    addr = inquirer.prompt([
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
        if config["id_bind"] != 0 and ("buyer_info" not in config):
            url = "https://show.bilibili.com/api/ticket/buyer/list"
            response = session.get(url, headers=headers)
            if response.status_code == 412:
                logger.error("被412风控，请联系作者")
            buyer_infos = response.json()["data"]["list"]
            config["buyer_info"] = []
            if len(buyer_infos) == 0:
                logger.error("未找到购票人，请前往实名添加购票人")
            else:
                multiselect = True
            if config["id_bind"] == 1:
                logger.info("本项目只能购买一人票")
                multiselect = False
            if multiselect:
                buyerids = inquirer.prompt([
                    inquirer.Checkbox(
                        "buyerids",
                        message="请选择购票人",
                        choices=[f"{i}. {buyer_infos[i]['name']} {buyer_infos[i]['personal_id']} {buyer_infos[i]['tel']}" for i in range(len(buyer_infos))],
                        validate=lambda _, x: len(x) > 0
                    )
                ])["buyerids"]
                buyerids = [int(i.split(".")[0]) for i in buyerids]
                config["buyer_info"] = []
                for select in buyerids:
                    config["buyer_info"].append(
                        buyer_infos[int(select)]
                    )  # type: ignore
                    # type: ignore
                    logger.info(
                        "已选择购票人" + buyer_infos[int(select)]["name"] + " " + buyer_infos[int(select)]["personal_id"] + " " + buyer_infos[int(select)]["tel"]
                    )
            else:
                index = inquirer.prompt([
                    inquirer.List("index", message="请选择购票人", choices=[{"name": f"{i}. {buyer_infos[i]['name']} {buyer_infos[i]['personal_id']} {buyer_infos[i]['tel']}", "value": i} for i in range(len(buyer_infos))])
                ])["index"].split(".")[0]
                config["buyer_info"].append(buyer_infos[index])
                logger.info("已选择购票人" + buyer_infos[index]["name"] + " " + buyer_infos[index]["personal_id"] + " " + buyer_infos[index]["tel"])
            if "count" not in config:
                config["count"] = len(config["buyer_info"])
            config["buyer_info"] = json.dumps(config["buyer_info"])
        if config["id_bind"] == 0 and (
            "buyer" not in config or "tel" not in config
        ):
            logger.info("请添加联系人信息")
            config["buyer"] = inquirer.prompt([
                inquirer.Text("buyer", message="联系人姓名")
            ])["buyer"]
            config["tel"] = inquirer.prompt([
                inquirer.Text("tel", message="联系人手机号", validate=lambda _, x: len(x) == 11)
            ])["tel"]
            if "count" not in config:
                config["count"] = inquirer.prompt([
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
                f"共 {config['count']} 张 {config['ticket_desc']} 票，单张价格为 {int(config['pay_money'])/100}，总价为{config['all_price'] / 100}"
            )
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f)
        sentry_sdk.capture_message("config complete")
        BHYG = BilibiliHyg(config, sentry_sdk, kdl_client, session)
        run(BHYG)
    except KeyboardInterrupt:
        logger.info("已手动退出")
        return
    except Exception as e:
        track = sentry_sdk.capture_exception(e)
        logger.exception("程序出现错误，错误信息：" + str(e))
        logger.error("错误追踪ID(可提供给开发者)：" + str(track))
        return
    return


if __name__ == "__main__":
    main()
    from sentry_sdk import Hub

    client = Hub.current.client
    if client is not None:
        client.close(timeout=2.0)
    logger.info("已安全退出，您可以关闭窗口")
    time.sleep(10)
