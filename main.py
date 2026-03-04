import sys
import shutil
import time
import tempfile
import os

import atexit
import qrcode
import questionary
import sentry_sdk
from loguru import logger

from api import BHYG

BANNER = """
██████╗ ██╗  ██╗██╗   ██╗ ██████╗ 
██╔══██╗██║  ██║╚██╗ ██╔╝██╔════╝ 
██████╔╝███████║ ╚████╔╝ ██║  ███╗
██╔══██╗██╔══██║  ╚██╔╝  ██║   ██║
██████╔╝██║  ██║   ██║   ╚██████╔╝
╚═════╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝ 

3 年过去，愿初心仍在。
"""


def is_terminal_available():
    try:
        return sys.stdout.isatty() and sys.stderr.isatty()
    except (AttributeError, OSError):
        return False


def exit_handler():
    logger.info("Exiting...")
    sentry_sdk.capture_message(
        "Exit",
        level="info",
    )
    sentry_sdk.flush()
    import time

    logger.info("Wait 10s to exit...")
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        sys.exit(1)
    return

def select_ticket():
    SALE_STATUS_MAP = {
        1: client.i18n("sale_status_1"),
        2: client.i18n("sale_status_2"),
        3: client.i18n("sale_status_3"),
        4: client.i18n("sale_status_4"),
        5: client.i18n("sale_status_5"),
        6: client.i18n("sale_status_6"),
        8: client.i18n("sale_status_8"),
        9: client.i18n("sale_status_9"),
    }
    project_id = questionary.text(
        client.i18n("project_id"), validate=lambda text: text.isdigit()
    ).ask()
    if not project_id:
        logger.info(client.i18n("canceled"))
        return
    resp = client.client.get(
        "https://show.bilibili.com/api/ticket/project/getV2?version=134&id={}".format(
            project_id
        )
    )
    logger.debug(resp)
    if resp["code"] != 0:
        logger.warning(
            client.i18n("get_project_failed").format(message=resp["message"])
        )
        return
    client.config["project_id"] = int(project_id)
    sentry_sdk.set_tag("project_id", project_id)
    logger.info(client.i18n("project_name").format(name=resp["data"]["name"]))
    ticket_name = f"{resp['data']['name']} "
    client.config["hotProject"] = resp["data"].get("hotProject", False)
    client.config["project_buyer_info"] = resp["data"].get("buyer_info", "")
    if client.config["hotProject"]:
        logger.warning(client.i18n("hot_project"))
    client.config["id_bind"] = resp["data"]["id_bind"]
    client.config["is_changfan"] = False
    changfan = client.client.get(
        "https://show.bilibili.com/api/ticket/linkgoods/list?project_id={}&page_type=0".format(
            project_id
        )
    )
    if changfan["code"] != 0:
        logger.warning(
            client.i18n("get_changfan_failed").format(message=changfan["message"])
        )
    elif changfan["data"]["total"] == 0:
        pass
    else:
        logger.info(client.i18n("have_changfan_msg"))
        is_changfan = questionary.select(
            client.i18n("is_changfan"),
            choices=[
                client.i18n("no"),
                client.i18n("yes"),
            ],
        ).ask()
        if is_changfan == client.i18n("yes"):
            logger.info(client.i18n("select_changfan_id_bind_type_prompt"))
            id_bind = questionary.select(
                client.i18n("select_changfan_id_bind_type"),
                choices=[
                    questionary.Choice(client.i18n("id_bind_type_0"), value=0),
                    questionary.Choice(client.i18n("id_bind_type_1"), value=1),
                    questionary.Choice(client.i18n("id_bind_type_2"), value=2),
                ],
            ).ask()
            client.config["id_bind"] = id_bind
            client.config["is_changfan"] = True
            linkgood = questionary.select(
                client.i18n("select_changfan"),
                choices=[
                    questionary.Choice(
                        f"{linkgood['detail']['name']} {SALE_STATUS_MAP[linkgood['sale_flag']]}",
                        value=linkgood,
                    )
                    for linkgood in changfan["data"]["list"]
                ],
            ).ask()
            if not linkgood:
                logger.info(client.i18n("canceled"))
                return
            client.config["linkgood_id"] = int(linkgood["id"])
            client.config["project_id"] = int(linkgood["item_id"])
            resp = client.client.get(
                f"https://show.bilibili.com/api/ticket/linkgoods/detail?link_id={client.config['linkgood_id']}"
            )
            if resp["code"] != 0:
                logger.warning(
                    client.i18n("get_changfan_failed").format(message=resp["message"])
                )
                return
            screens = resp["data"]["specs_list"]
    if not client.config.get("is_changfan", False):
        # Cyclicity check, ref #2
        if resp["data"].get("project_type", 1) == 2:
            logger.info(client.i18n("have_sales_dates_msg"))
            sales_dates = resp["data"]["sales_dates"]
            sale_date = questionary.select(
                client.i18n("select_sales_date"),
                choices=[
                    questionary.Choice(sales_date["date"]) for sales_date in sales_dates
                ],
            ).ask()
            if not sale_date:
                logger.info(client.i18n("canceled"))
                return
            resp = client.client.get(
                f"https://show.bilibili.com/api/ticket/project/infoByDate?id={project_id}&date={sale_date}"
            )
            if resp["code"] != 0:
                logger.warning(
                    client.i18n("get_project_failed").format(message=resp["message"])
                )
                return
        screens = resp["data"]["screen_list"]
        if len(screens) == 0:
            logger.warning(client.i18n("no_screen"))
            return
    screen = questionary.select(
        client.i18n("select_screen"),
        choices=[
            questionary.Choice(
                client.i18n("screen_info").format(
                    name=screen["name"],
                    sale_status=SALE_STATUS_MAP[screen["sale_flag_number"]],
                ),
                value=screen,
            )
            for screen in screens
        ],
    ).ask()
    if not screen:
        logger.info(client.i18n("canceled"))
        return
    client.config["screen_id"] = int(screen["id"])
    ticket_name += f"{screen['name']} "
    sku = questionary.select(
        client.i18n("select_sku"),
        choices=[
            questionary.Choice(
                client.i18n("sku_info").format(
                    name=sku["desc"],
                    price=sku["price"] / 100,
                    sale_status=SALE_STATUS_MAP[sku["sale_flag_number"]],
                ),
                value=sku,
            )
            for sku in screen["ticket_list"]
        ],
    ).ask()
    if not sku:
        logger.info(client.i18n("canceled"))
        return
    try:
        client.config["sale_start_time"] = int(
            time.mktime(time.strptime(sku["sale_start"], "%Y-%m-%d %H:%M:%S"))
        )
        client.config["pay_money"] = sku["price"]
    except ValueError:
        logger.warning(client.i18n("sale_start_time_not_found"))
        client.config["sale_start_time"] = 0
    client.config["sku_id"] = int(sku["id"])
    ticket_name += f"{sku['desc']}"
    client.config["count"] = questionary.text(
        client.i18n("select_count"), validate=lambda text: text.isdigit()
    ).ask()
    if not client.config["count"]:
        logger.info(client.i18n("canceled"))
        return
    client.config["count"] = int(client.config["count"])
    logger.warning(client.i18n("unsupported_order_type_warining"))
    client.config["order_type"] = 1
    client.config["pay_money"] = questionary.text(
        client.i18n("select_pay_money"),
        validate=lambda text: text.isdigit(),
        default=str(client.calculate_pay_money()),
    ).ask()
    if not client.config["pay_money"]:
        logger.info(client.i18n("canceled"))
        return
    client.config["pay_money"] = int(client.config["pay_money"])
    client.config["ticket_name"] = ticket_name
    # TODO: Order Type
    # 1. 正常
    # 2. group_buy promotion 团购
    # 3. rebate 票票团
    # 5. sale_type=3 crowd-funding 众筹
    # 6. act discount 早鸟等活动
    client.save_config()
    # TODO: 检查限购


def start_ticket():
    logger.info(client.i18n("in_todo"))
    pass


def select_buyer():
    client.config["id_buyer"] = []
    client.config["buyer"] = ""
    client.config["tel"] = ""
    if client.config["id_bind"] == 0:
        # only contact
        client.config["buyer"] = questionary.text(
            client.i18n("buyer_name"), validate=lambda text: len(text) > 0
        ).ask()
        client.config["tel"] = questionary.text(
            client.i18n("buyer_phone"),
            validate=lambda text: text.isdigit() and len(text) == 11,
        ).ask()
        logger.debug(
            "Buyer info: {} {}".format(client.config["buyer"], client.config["tel"])
        )
        pass
    elif client.config["id_bind"] == 1 or client.config["id_bind"] == 2:
        # 单号单证/单票单证
        id_type_name = {
            0: client.i18n("id_type_idcard"),
            1: client.i18n("id_type_passport"),
            2: client.i18n("id_type_hk_macau"),
            3: client.i18n("id_type_taiwan"),
        }
        buyer_list = client.client.get(
            "https://show.bilibili.com/api/ticket/buyer/list?nomask=1"
        )
        logger.debug(buyer_list)
        if buyer_list["code"] != 0:
            logger.warning(
                client.i18n("get_buyer_failed").format(message=buyer_list["message"])
            )
            return
        if len(buyer_list["data"]["list"]) == 0:
            logger.warning(client.i18n("no_buyer"))
            return
        selected_buyers = questionary.checkbox(
            client.i18n("select_buyer"),
            choices=[
                questionary.Choice(
                    client.i18n("buyer_info").format(
                        name=buyer["name"],
                        tel=buyer["tel"],
                        personal_id=buyer["personal_id"],
                        id_type=id_type_name[buyer["id_type"]],
                    ),
                    value=buyer,
                )
                for buyer in buyer_list["data"]["list"]
            ],
            validate=lambda buyers: len(buyers) == client.config["count"],
        ).ask()
        if not selected_buyers:
            logger.info(client.i18n("canceled"))
            return
        client.config["id_buyer"] = []
        for buyer in selected_buyers:
            client.config["id_buyer"].append(
                {
                    "id": buyer["id"],
                    "name": buyer["name"],
                    "tel": buyer["tel"],
                    "personal_id": buyer["personal_id"],
                    "id_type": buyer["id_type"],
                }
            )
            client.config["uid_buyer"][buyer["id"]] = buyer["uid"]
        logger.debug("Selected buyers: {}".format(client.config["id_buyer"]))
        if client.config.get("is_changfan", False):
            client.config["buyer"] = questionary.text(
                client.i18n("buyer_name"), validate=lambda text: len(text) > 0
            ).ask()
            client.config["tel"] = questionary.text(
                client.i18n("buyer_phone"),
                validate=lambda text: text.isdigit() and len(text) == 11,
            ).ask()
            logger.debug(
                "Buyer info: {} {}".format(client.config["buyer"], client.config["tel"])
            )
    else:
        logger.error(client.i18n("invalid_id_bind"))
        return
    client.save_config()


def main():
    global client, normal_exit
    # Init

    print(BANNER)

    atexit.register(exit_handler)
    normal_exit = False

    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))


    print("Initializing...")

    if not is_terminal_available():
        print(
            "BHYG 需要终端交互才能使用，请在终端环境使用\nBHYG needs terminal to use, please use in terminal environment"
        )
        sys.exit(1)

    if getattr(sys, "frozen", False):
        executable_name = os.path.basename(sys.executable)
        if "bhyg" not in executable_name.lower():
            print(client.i18n("maybe_violated"))
            sys.exit(1)

    client = BHYG()

    while True:
        sentry_sdk.capture_message(
            "Entered Main Menu",
            level="info",
        )
        main_menu = [
            client.i18n("select_ticket_info"),
            client.i18n("select_buyer"),
            client.i18n("start_ticket"),
            client.i18n("single_test_order"),
            client.i18n("select_after_success_action"),
            client.i18n("test_push"),
            client.i18n("prefill_phone"),
            client.i18n("check_order"),
            client.i18n("change_order_interval"),
            client.i18n("change_delta"),
            client.i18n("switch_account"),
            client.i18n("check_info"),
            client.i18n("set_ip"),
            client.i18n("set_cptoken_manually"),
            client.i18n("change_after_sale_begin_delay"),
            client.i18n("status_code_meaning"),
            client.i18n("select_language"),
            client.i18n("clean_cache"),
            client.i18n("exit"),
        ]
        main_menu.insert(4, client.i18n("solve_captcha"))
        main_menu.insert(4, client.i18n("lottery"))
        main_menu.insert(4, client.i18n("switch_use_prepare"))
        main_menu.insert(4, client.i18n("bws"))
        main_menu.insert(4, client.i18n("change_check_stock_interval"))
        main_menu.insert(4, client.i18n("change_check_stock_available_dalay"))
        main_menu.insert(4, client.i18n("switch_check_stock"))
        action = questionary.select(
            client.i18n("select_action"),
            choices=main_menu,
        ).ask()
        try:
            logger.debug("Selected action: {}".format(action))
            try:
                if action == client.i18n("select_ticket_info"):
                    select_ticket()
                elif action == client.i18n("status_code_meaning"):
                    logger.info(client.i18n("status_code_meaning_content"))
                elif action == client.i18n("select_buyer"):
                    if not client.check_select_sku_complete():
                        logger.warning(client.i18n("select_sku_not_complete"))
                        continue
                    select_buyer()
                elif action == client.i18n("start_ticket"):
                    client.rush_mode()
                elif action == client.i18n("set_ip"):
                    client.set_ip()
                elif action == client.i18n("single_test_order"):
                    if not client.check_select_sku_complete():
                        logger.warning(client.i18n("select_sku_not_complete"))
                        continue
                    if not client.check_select_buyer_complete():
                        logger.warning(client.i18n("select_buyer_not_complete"))
                        continue
                    logger.info(client.get_current_info())
                    confirm = questionary.confirm(client.i18n("confirm_to_order")).ask()
                    if not confirm:
                        continue
                    if client.config["sale_start_time"] > int(time.time()):
                        logger.warning(client.i18n("sale_not_started_warning"))
                        logger.warning(client.i18n("sale_not_started_warning"))
                        logger.warning(client.i18n("sale_not_started_warning"))
                        confirm = questionary.confirm(
                            client.i18n("confirm_continue")
                        ).ask()
                        if not confirm:
                            continue
                    client.do_order_create()
                elif action == client.i18n("solve_captcha"):
                    client.solve_captcha()
                elif action == client.i18n("set_cptoken_manually"):
                    ctoken = questionary.text(
                        client.i18n("set_ctoken_manually_prompt")
                    ).ask()
                    client.config["ctoken"] = ctoken
                    ptoken = questionary.text(
                        client.i18n("set_ptoken_manually_prompt")
                    ).ask()
                    client.config["ptoken"] = ptoken
                    client.save_config()
                elif action == client.i18n("check_order"):
                    client.check_order()
                elif action == client.i18n("switch_use_prepare"):
                    use_prepare = questionary.select(
                        client.i18n("switch_use_prepare"),
                        choices=[
                            client.i18n("yes"),
                            client.i18n("no"),
                        ],
                    ).ask()
                    if use_prepare == client.i18n("yes"):
                        client.config["use_prepare_token"] = True
                    else:
                        client.config["use_prepare_token"] = False
                    client.save_config()
                elif action == client.i18n("bws"):
                    client.rush_bws()
                elif action == client.i18n("change_after_sale_begin_delay"):
                    delay = questionary.text(
                        client.i18n("change_after_sale_begin_delay_prompt"),
                        default=str(
                            int(client.config.get("after_sale_begin_delay", 0) * 1000)
                        ),
                        validate=lambda text: text.isdigit(),
                    ).ask()
                    client.config["after_sale_begin_delay"] = int(delay) / 1000
                    client.save_config()
                elif action == client.i18n("select_after_success_action"):
                    actions = questionary.checkbox(
                        client.i18n("select_after_success_action"),
                        choices=[
                            client.i18n("gotify_push"),
                            client.i18n("ob11_push"),
                            client.i18n("milky_push"),
                            client.i18n("bark_push"),
                            client.i18n("ntfy_push"),
                            client.i18n("desktop_notify"),
                            client.i18n("pushplus_push"),
                            client.i18n("server_chan_push"),
                            client.i18n("run_command"),
                        ],
                    ).ask()
                    if actions is None:
                        logger.info(client.i18n("canceled"))
                        continue
                    push_config = {"push_actions": []}
                    if client.i18n("gotify_push") in actions:
                        push_config["push_actions"].append("gotify")
                        gotify_config = {}
                        default_token = ""
                        default_server = "https://gotify.rakuyoudesu.com"
                        if "push_config" in client.config:
                            if "gotify" in client.config["push_config"]:
                                if "token" in client.config["push_config"]["gotify"]:
                                    default_token = client.config["push_config"][
                                        "gotify"
                                    ]["token"]
                                if "server" in client.config["push_config"]["gotify"]:
                                    default_server = client.config["push_config"][
                                        "gotify"
                                    ]["server"]
                        gotify_config["server"] = questionary.text(
                            client.i18n("gotify_server"),
                            default=default_server,
                            validate=lambda text: (
                                text.startswith("http://")
                                or text.startswith("https://")
                            )
                            and text.count("/") == 2,
                        ).ask()
                        gotify_config["token"] = questionary.text(
                            client.i18n("gotify_token"), default=default_token
                        ).ask()
                        if (
                            gotify_config["server"] == None
                            or gotify_config["token"] == None
                        ):
                            push_config["push_actions"].remove("gotify")
                            logger.info(client.i18n("canceled"))
                            continue
                        push_config["gotify"] = gotify_config
                    if client.i18n("ob11_push") in actions:
                        push_config["push_actions"].append("ob11")
                        ob11_config = {}
                        default_token = ""
                        default_server = ""
                        if "push_config" in client.config:
                            if "ob11" in client.config["push_config"]:
                                if "token" in client.config["push_config"]["ob11"]:
                                    default_token = client.config["push_config"][
                                        "ob11"
                                    ]["token"]
                                if "server" in client.config["push_config"]["ob11"]:
                                    default_server = client.config["push_config"][
                                        "ob11"
                                    ]["server"]
                        ob11_config["server"] = questionary.text(
                            client.i18n("ob11_server"),
                            default=default_server,
                            validate=lambda text: (
                                text.startswith("http://")
                                or text.startswith("https://")
                            )
                            and text.count("/") == 2,
                        ).ask()
                        ob11_config["token"] = questionary.text(
                            client.i18n("ob11_token"), default=default_token
                        ).ask()
                        ob11_config["send_type"] = questionary.select(
                            client.i18n("ob11_send_type"),
                            choices=[
                                client.i18n("ob11_send_type_private"),
                                client.i18n("ob11_send_type_group"),
                            ],
                        ).ask()
                        if ob11_config["send_type"] == client.i18n(
                            "ob11_send_type_private"
                        ):
                            ob11_config["send_type"] = "private"
                        elif ob11_config["send_type"] == client.i18n(
                            "ob11_send_type_group"
                        ):
                            ob11_config["send_type"] = "group"
                        else:
                            logger.error(client.i18n("invalid_send_type"))
                            continue
                        ob11_config["send_target"] = questionary.text(
                            client.i18n("ob11_send_target"),
                            validate=lambda text: text.isdigit(),
                        ).ask()
                        ob11_config["send_target"] = int(ob11_config["send_target"])
                        if (
                            ob11_config["send_target"] == None
                            or ob11_config["token"] == None
                            or ob11_config["server"] == None
                        ):
                            push_config["push_actions"].remove("ob11")
                            logger.info(client.i18n("canceled"))
                            continue
                        push_config["ob11"] = ob11_config
                    if client.i18n("milky_push") in actions:
                        push_config["push_actions"].append("milky")
                        milky_config = {}
                        default_token = ""
                        default_server = ""
                        if "push_config" in client.config:
                            if "milky" in client.config["push_config"]:
                                if "token" in client.config["push_config"]["milky"]:
                                    default_token = client.config["push_config"][
                                        "milky"
                                    ]["token"]
                                if "server" in client.config["push_config"]["milky"]:
                                    default_server = client.config["push_config"][
                                        "milky"
                                    ]["server"]
                        milky_config["server"] = questionary.text(
                            client.i18n("milky_server"),
                            default=default_server,
                            validate=lambda text: (
                                text.startswith("http://")
                                or text.startswith("https://")
                            )
                            and text.count("/") == 2,
                        ).ask()
                        milky_config["token"] = questionary.text(
                            client.i18n("milky_token"), default=default_token
                        ).ask()
                        milky_config["send_type"] = questionary.select(
                            client.i18n("milky_send_type"),
                            choices=[
                                client.i18n("milky_send_type_private"),
                                client.i18n("milky_send_type_group"),
                            ],
                        ).ask()
                        if milky_config["send_type"] == client.i18n(
                            "milky_send_type_private"
                        ):
                            milky_config["send_type"] = "private"
                        elif milky_config["send_type"] == client.i18n(
                            "milky_send_type_group"
                        ):
                            milky_config["send_type"] = "group"
                        else:
                            logger.error(client.i18n("invalid_send_type"))
                            continue
                        milky_config["send_target"] = questionary.text(
                            client.i18n("milky_send_target"),
                            validate=lambda text: text.isdigit(),
                        ).ask()
                        milky_config["send_target"] = int(milky_config["send_target"])
                        if (
                            milky_config["send_target"] == None
                            or milky_config["token"] == None
                            or milky_config["server"] == None
                        ):
                            push_config["push_actions"].remove("milky")
                            logger.info(client.i18n("canceled"))
                            continue
                        push_config["milky"] = milky_config
                    if client.i18n("bark_push") in actions:
                        push_config["push_actions"].append("bark")
                        bark_config = {}
                        default_key = ""
                        default_server = "https://api.day.app"
                        if "push_config" in client.config:
                            if "bark" in client.config["push_config"]:
                                if "key" in client.config["push_config"]["bark"]:
                                    default_key = client.config["push_config"]["bark"][
                                        "key"
                                    ]
                                if "server" in client.config["push_config"]["bark"]:
                                    default_server = client.config["push_config"][
                                        "bark"
                                    ]["server"]
                        bark_config["server"] = questionary.text(
                            client.i18n("bark_server"),
                            default=default_server,
                            validate=lambda text: (
                                text.startswith("http://")
                                or text.startswith("https://")
                            )
                            and text.count("/") == 2,
                        ).ask()
                        bark_config["key"] = questionary.text(
                            client.i18n("bark_key"),
                            default=default_key,
                            validate=lambda text: text.count("/") == 0,
                        ).ask()
                        bark_config["enhanced"] = questionary.confirm(
                            client.i18n("bark_enhanced")
                        ).ask()
                        if (
                            bark_config["key"] == None
                            or bark_config["server"] == None
                            or bark_config["enhanced"] == None
                        ):
                            push_config["push_actions"].remove("bark")
                            logger.info(client.i18n("canceled"))
                            continue
                        push_config["bark"] = bark_config
                    if client.i18n("ntfy_push") in actions:
                        push_config["push_actions"].append("ntfy")
                        ntfy_config = {}
                        default_server = "https://ntfy.sh"
                        default_topic = ""
                        if "push_config" in client.config:
                            if "ntfy" in client.config["push_config"]:
                                if "server" in client.config["push_config"]["ntfy"]:
                                    default_server = client.config["push_config"][
                                        "ntfy"
                                    ]["server"]
                                if "topic" in client.config["push_config"]["ntfy"]:
                                    default_topic = client.config["push_config"][
                                        "ntfy"
                                    ]["topic"]
                        ntfy_config["server"] = questionary.text(
                            client.i18n("ntfy_server"),
                            default=default_server,
                            validate=lambda text: (
                                text.startswith("http://")
                                or text.startswith("https://")
                            )
                            and text.count("/") == 2,
                        ).ask()
                        ntfy_config["topic"] = questionary.text(
                            client.i18n("ntfy_topic"), default=default_topic
                        ).ask()
                        if (
                            ntfy_config["topic"] == None
                            or ntfy_config["server"] == None
                        ):
                            push_config["push_actions"].remove("ntfy")
                            logger.info(client.i18n("canceled"))
                            continue
                        push_config["ntfy"] = ntfy_config
                    if client.i18n("desktop_notify") in actions:
                        push_config["push_actions"].append("desktop_notify")
                        desktop_notify_config = {}
                        desktop_notify_config["need_sound"] = questionary.confirm(
                            client.i18n("need_sound")
                        ).ask()
                        if desktop_notify_config["need_sound"]:
                            # make sure only a-zA-Z0-9_.- are in the file name
                            import re

                            desktop_notify_config["sound_path"] = questionary.path(
                                client.i18n("sound_path"),
                                validate=lambda text: bool(
                                    re.match(r"^[a-zA-Z0-9_.-]+$", text)
                                ),
                            ).ask()
                            if desktop_notify_config["sound_path"] == None:
                                logger.info(client.i18n("canceled"))
                                desktop_notify_config["sound_path"] = ""
                        else:
                            desktop_notify_config["sound_path"] = ""
                        push_config["desktop_notify"] = desktop_notify_config
                    if client.i18n("pushplus_push") in actions:
                        push_config["push_actions"].append("pushplus")
                        pushplus_config = {}
                        default_token = ""
                        if "push_config" in client.config:
                            if "pushplus" in client.config["push_config"]:
                                if "token" in client.config["push_config"]["pushplus"]:
                                    default_token = client.config["push_config"][
                                        "pushplus"
                                    ]["token"]
                        pushplus_config["token"] = questionary.text(
                            client.i18n("pushplus_token"), default=default_token
                        ).ask()
                        if pushplus_config["token"] == None:
                            push_config["push_actions"].remove("pushplus")
                            logger.info(client.i18n("canceled"))
                            continue
                        push_config["pushplus"] = pushplus_config
                    if client.i18n("server_chan_push") in actions:
                        push_config["push_actions"].append("server_chan")
                        server_chan_config = {}
                        default_send_key = ""
                        if "push_config" in client.config:
                            if "server_chan" in client.config["push_config"]:
                                if (
                                    "send_key"
                                    in client.config["push_config"]["server_chan"]
                                ):
                                    default_send_key = client.config["push_config"][
                                        "server_chan"
                                    ]["send_key"]
                        server_chan_config["send_key"] = questionary.text(
                            client.i18n("server_chan_send_key"),
                            default=default_send_key,
                        ).ask()
                        if server_chan_config["send_key"] == None:
                            push_config["push_actions"].remove("server_chan")
                            logger.info(client.i18n("canceled"))
                            continue
                        push_config["server_chan"] = server_chan_config
                    if client.i18n("run_command") in actions:
                        push_config["push_actions"].append("run_command")
                        run_command_config = {}
                        default_command = ""
                        if "push_config" in client.config:
                            if "run_command" in client.config["push_config"]:
                                if (
                                    "command"
                                    in client.config["push_config"]["run_command"]
                                ):
                                    default_command = client.config["push_config"][
                                        "run_command"
                                    ]["command"]
                        logger.info(client.i18n("run_command_help"))
                        run_command_config["command"] = questionary.text(
                            client.i18n("run_command_command"), default=default_command
                        ).ask()
                        if run_command_config["command"] == None:
                            push_config["push_actions"].remove("run_command")
                            logger.info(client.i18n("canceled"))
                            continue
                        push_config["run_command"] = run_command_config
                    client.config["push_config"] = push_config
                    client.save_config()
                elif action == client.i18n("lottery"):
                    reward_id = questionary.text(
                        client.i18n("select_reward_id"),
                        validate=lambda text: text.isdigit(),
                    ).ask()
                    activity_code = questionary.text(
                        client.i18n("select_activity_code")
                    ).ask()
                    if not reward_id or not activity_code:
                        logger.info(client.i18n("canceled"))
                        continue
                    reward_id = int(reward_id)
                    client.client.session.headers.update(
                        {"Referer": "https://activity.bilibili.com/"}
                    )
                    while True:
                        try:
                            data = {
                                "csrf": client.client.session.cookies.get("bili_jct"),
                                "ts": int(time.time()),
                                "inputMap": {"rewardId": reward_id},
                                "name": "lottery_common_doDirectReceive",
                                "activityCode": activity_code,
                                "t": int(time.time() * 1000),
                            }
                            resp = client.client.post(
                                "https://api.bilibili.com/pgc/activity/dokodemoDoor/req/lottery_common_doDirectReceive",
                                json=data,
                            )
                            logger.debug(resp)
                            if resp["code"] != 0:
                                logger.warning(
                                    client.i18n("get_reward_failed").format(
                                        message=resp["message"]
                                    )
                                )
                            else:
                                if resp["data"]["result"] == "SUCCESS":
                                    logger.success(client.i18n("get_reward_success"))
                                    break
                                else:
                                    logger.warning(
                                        client.i18n("get_reward_failed").format(
                                            message=resp["data"]["msg"]
                                        )
                                    )
                        except Exception as e:
                            logger.exception(e)
                            track = sentry_sdk.capture_exception(e)
                            logger.error(
                                client.i18n("error_occurred").format(trace=track)
                            )
                            continue
                elif action == client.i18n("test_push"):
                    client.test_push()
                elif action == client.i18n("prefill_phone"):
                    phone = questionary.text(
                        client.i18n("prefill_phone"),
                        validate=lambda text: text.isdigit(),
                    ).ask()
                    if not phone:
                        logger.info(client.i18n("canceled"))
                        continue
                    client.config["phone"] = phone
                    client.save_config()
                elif action == client.i18n("change_order_interval"):
                    logger.warning(client.i18n("change_order_interval_warning"))
                    interval = questionary.text(
                        client.i18n("change_order_interval"),
                        validate=lambda text: text.isdigit(),
                        default="300",
                    ).ask()
                    if not interval:
                        logger.info(client.i18n("canceled"))
                        continue
                    client.config["order_interval"] = int(interval) / 1000
                    client.save_config()
                elif action == client.i18n("switch_check_stock"):
                    check_stock = questionary.select(
                        client.i18n("switch_check_stock"),
                        choices=[
                            client.i18n("yes"),
                            client.i18n("no"),
                        ],
                        default=client.i18n("yes")
                        if client.config.get("enable_check_stock", True)
                        else client.i18n("no"),
                    ).ask()
                    if check_stock == client.i18n("yes"):
                        client.config["enable_check_stock"] = True
                    else:
                        client.config["enable_check_stock"] = False
                    client.save_config()
                elif action == client.i18n("change_check_stock_interval"):
                    interval = questionary.text(
                        client.i18n("change_check_stock_interval"),
                        validate=lambda text: text.isdigit(),
                        default="0",
                    ).ask()
                    if not interval:
                        logger.info(client.i18n("canceled"))
                        continue
                    client.config["check_stock_interval"] = int(interval) / 1000
                    client.save_config()
                elif action == client.i18n("change_check_stock_available_dalay"):
                    delay = questionary.text(
                        client.i18n("change_check_stock_available_dalay"),
                        validate=lambda text: text.isdigit(),
                        default="0",
                    ).ask()
                    if not delay:
                        logger.info(client.i18n("canceled"))
                        continue
                    client.config["stock_check_available_dalay"] = int(delay) / 1000
                    client.save_config()
                elif action == client.i18n("change_delta"):
                    logger.warning(client.i18n("change_delta_info"))
                    interval = questionary.text(
                        client.i18n("change_delta"),
                        validate=lambda text: text.isdigit(),
                        default="50",
                    ).ask()
                    if not interval:
                        logger.info(client.i18n("canceled"))
                        continue
                    client.config["delta"] = int(interval) / 1000
                    client.save_config()
                elif action == client.i18n("switch_account"):
                    client.switch_account()
                elif action == client.i18n("switch_config"):
                    client.switch_config()
                elif action == client.i18n("check_info"):
                    info = client.get_current_info()
                    logger.info(info)
                    questionary.confirm(client.i18n("press_enter_to_continue")).ask()
                elif action == client.i18n("select_language"):
                    client.select_language()
                elif action == client.i18n("clean_cache"):
                    try:
                        temp_dir = tempfile.gettempdir()
                        for item in os.listdir(temp_dir):
                            if item.startswith("_MEI"):
                                try:
                                    shutil.rmtree(os.path.join(temp_dir, item))
                                except Exception as e:
                                    pass
                        logger.success(client.i18n("clean_cache_ok"))
                    except Exception as e:
                        logger.error(client.i18n("clean_cache_failed").format(error=e))
                elif action == None or action == client.i18n("exit"):
                    logger.info(client.i18n("exit"))
                    sentry_sdk.capture_message(
                        "Exit",
                        level="info",
                    )
                    normal_exit = True
                    sys.exit(0)
                else:
                    logger.error(client.i18n("invalid_action"))
                    continue
            except KeyboardInterrupt:
                continue
            except:
                raise
        except Exception as e:
            logger.exception(e)
            track = sentry_sdk.capture_exception(e)
            logger.error(client.i18n("error_occurred").format(trace=track))
            continue
