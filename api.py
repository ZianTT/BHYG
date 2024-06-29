import json
import random
import time
import urllib.parse
import hashlib
import hmac

import qrcode
import requests
from loguru import logger

from i18n import *

from utils import save, load
from globals import *

class BilibiliHyg:
    global sdk
    def __init__(self, config, sdk,client,session):
        self.waited = False
        self.sdk = sdk
        self.config = config
        self.config["gaia_vtoken"] = None
        self.session = requests.Session()
        if "user-agent" in self.config:
            self.headers = {
                "User-Agent": self.config["user-agent"],
            }
        else:
            self.headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            }

        self.headers["Cookie"] = self.config["cookie"]
        if self.config["proxy"]:
            if self.config["proxy_channel"] != "0":
                self.headers["kdl-tps-channel"] = config["proxy_channel"]

        self.client = client
        self.session = session
        if self.client != None:
            self.ip = self.client.tps_current_ip(sign_type="hmacsha1")
        if self.config["mode"] == 'time':
            logger.info(i18n_gt()["now_mode_time_on"])
            logger.info(i18n_gt()["wait_get_token"])
            while self.get_time() < self.config["time"]-15:
                time.sleep(10)
                logger.info(i18n_gt()["now_waiting_info"].format((self.config["time"]-self.get_time())))
            while self.get_time() < self.config["time"]:
                pass
        logger.info(i18n_gt()["get_token_finish"])
        self.token = self.get_token()
        logger.info(i18n_gt()["will_pay_bill"])

    def get_time(self):
        return float(time.time() + self.config["time_offset"])

    def get_ticket_status(self):
        url = (
            "https://show.bilibili.com/api/ticket/project/getV2?version=134&id="
            + self.config["project_id"]
        )
        try:
            response = self.session.get(url, headers=self.headers, timeout=1)
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ):
            logger.error(i18n_gt()["network_timeout"])
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                            i18n_gt()["manual_change_ip"].format(
                                self.client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                self.session.close()
                return self.get_ticket_status()
            return -1, 0
        try:
            if response.status_code == 412:
                logger.error(i18n_gt()["wind_control"])
                if self.config["proxy"]:
                    if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                        logger.info(
                            i18n_gt()["manual_change_ip"].format(
                                self.client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                    self.session.close()
                    return self.get_ticket_status()
                else:
                    self.risk = True
                    logger.error(i18n_gt()["net_method"])
                    input(i18n_gt()["res_3_returns"])
                    input(i18n_gt()["res_2_returns"])
                    input(i18n_gt()["res_1_return"])
                    return -1, 0
            screens = response.json()["data"]["screen_list"]
            # 找到 字段id为screen_id的screen
            screen = {}
            for i in range(len(screens)):
                if screens[i]["id"] == int(self.config["screen_id"]):
                    screen = screens[i]
                    break
            if screen == {}:
                logger.error(i18n_gt()["no_found_screen"])
                return -1, 0
            # 找到 字段id为sku_id的sku
            skus = screen["ticket_list"]
            sku = {}
            for i in range(len(skus)):
                if skus[i]["id"] == int(self.config["sku_id"]):
                    sku = skus[i]
                    break
            if sku == {}:
                logger.error(i18n_gt()["no_found_sku"])
                return -1, 0
            return int(sku["sale_flag_number"]), sku["clickable"]
        except:
            logger.error(i18n_gt()["may_wind_control"])
            return -1, 0

    def get_prepare(self):
        url = (
            "https://show.bilibili.com/api/ticket/order/prepare?project_id="
            + self.config["project_id"]
        )
        if self.config["gaia_vtoken"]:
            url += "&gaia_vtoken=" + self.config["gaia_vtoken"]
        data = {
            "project_id": self.config["project_id"],
            "screen_id": self.config["screen_id"],
            "order_type": self.config["order_type"],
            "count": self.config["count"],
            "sku_id": self.config["sku_id"],
            "token": "",
            "newRisk": "true",
            "requestSource": "neul-next",
        }
        if "act_id" in self.config:
            data["act_id"] = self.config["act_id"]
        response = self.session.post(url, headers=self.headers, data=data)
        if response.status_code == 412:
            logger.error(i18n_gt()["not_handled_412"])
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                            i18n_gt()["manual_change_ip"].format(
                                self.client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                self.session.close()
                return self.get_prepare()
        if response.json()["errno"] != 0 and response.json()["errno"] != -401:
            logger.error(response.json()["msg"])
        return response.json()["data"]

    def gee_verify(self, gt, challenge, token):
        from geetest import run
        time_start = time.time()
        self.captcha_data = run(gt, challenge, token, mode = self.config["captcha"], key = self.config["rrocr"])
        delta = time.time() - time_start
        self.sdk.metrics.distribution(
            key="gt_solve_time",
            value=delta*1000,
            unit="millisecond"
        )
        self.captcha_data["csrf"] = self.headers["Cookie"][
                        self.headers["Cookie"].index("bili_jct")
                        + 9 : self.headers["Cookie"].index("bili_jct")
                        + 41
                    ]
        self.captcha_data["token"] = token
        success = self.session.post(
                        "https://api.bilibili.com/x/gaia-vgate/v1/validate",
                        headers=self.headers,
                        data=self.captcha_data,
        ).json()["data"]["is_valid"]
        self.config["gaia_vtoken"] = token
        self.captcha_data = None
        if self.headers["Cookie"].find("x-bili-gaia-vtoken") != -1:
            self.headers["Cookie"] = self.headers["Cookie"].split(
                "; x-bili-gaia-vtoken"
            )[0]
        self.headers["Cookie"] += "; x-bili-gaia-vtoken=" + token
        save(self.config)
        return success

    def phone_verify(self, token):
        if "phone" in self.config:
            phone = self.config["phone"]
        else:
            phone = input(i18n_gt()["input_phone_num"]+": ")
        self.captcha_data = {
            "code": phone,
        }
        self.captcha_data["csrf"] = self.headers["Cookie"][
                        self.headers["Cookie"].index("bili_jct")
                        + 9 : self.headers["Cookie"].index("bili_jct")
                        + 41
                    ]
        self.captcha_data["token"] = token
        success = self.session.post(
                        "https://api.bilibili.com/x/gaia-vgate/v1/validate",
                        headers=self.headers,
                        data=self.captcha_data,
        ).json()["data"]["is_valid"]
        if not success:
            logger.error(i18n_gt()["input_verify_fail"])
            if "phone" in self.config:
                self.config.pop("phone")
            return False
        self.config["gaia_vtoken"] = token
        self.captcha_data = None
        if self.headers["Cookie"].find("x-bili-gaia-vtoken") != -1:
            self.headers["Cookie"] = self.headers["Cookie"].split(
                "; x-bili-gaia-vtoken"
            )[0]
        self.headers["Cookie"] += "; x-bili-gaia-vtoken=" + token
        save(self.config)
        return success

    def confirm_info(self, token):
        url = (
            "https://show.bilibili.com/api/ticket/order/confirmInfo?token="
            + token
            + "&timestamp="
            + str(int(time.time() * 1000))
            + "&project_id="
            + self.config["project_id"]
            + "&requestSource=neul-next"
        )
        response = self.session.get(url, headers=self.headers)
        if response.status_code == 412:
            logger.error(i18n_gt()["not_handled_412"])
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                            i18n_gt()["manual_change_ip"].format(
                                self.client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                self.session.close()
                return self.confirm_info(token)
        response = response.json()
        logger.info(i18n_gt()["info_confirmed"])
        logger.debug(response)
        self.config["order_type"] = response["data"]["order_type"]
        if response["data"]["act"] is not None:
            logger.info(i18n_gt()["info_discount"])
            self.config["act_id"] = response["data"]["act"]["act_id"]
        return

    def get_token(self):
        info = self.get_prepare()
        if info == {}:
            logger.warning(i18n_gt()["info_no_ticket"])
            time.sleep(1)
            return self.get_token()
        if info["token"]:
            logger.success(
                i18n_gt()["info_bill_ok"]
                + "https://show.bilibili.com/platform/confirmOrder.html?token="
                + info["token"]
            )
            self.sdk.add_breadcrumb(
                category="prepare",
                message=f'Order prepared as token:{info["token"]}',
                level="info",
            )
            try:
                self.confirm_info(info["token"])
            except:
                logger.error(i18n_gt()["info_bill_fail"])
                return self.get_token()
            return info["token"]
        else:
            logger.warning(i18n_gt()["info_wind_control"])
            self.sdk.add_breadcrumb(
                category="gaia",
                message="Gaia found",
                level="info",
            )
            riskParam = info["ga_data"]["riskParams"]
            # https://api.bilibili.com/x/gaia-vgate/v1/register
            risk = self.session.post(
                "https://api.bilibili.com/x/gaia-vgate/v1/register",
                headers=self.headers,
                data=riskParam,
            ).json()
            while risk["code"] != 0:
                risk = self.session.post(
                    "https://api.bilibili.com/x/gaia-vgate/v1/register",
                    headers=self.headers,
                    data=riskParam,
                ).json()
            if risk["data"]["type"] == "geetest":
                logger.warning(i18n_gt()["type_captcha"])
                gt, challenge, token = (
                    risk["data"]["geetest"]["gt"],
                    risk["data"]["geetest"]["challenge"],
                    risk["data"]["token"],
                )
                cap_data = self.gee_verify(gt, challenge, token)
                while cap_data == False:
                    logger.error(i18n_gt()["input_verify_fail"])
                    return self.get_token()
                logger.info(i18n_gt()["input_verify_success"])
            elif risk["data"]["type"] == "phone":
                logger.warning(i18n_gt()["type_mobile"])
                token = risk["data"]["token"]
                cap_data = self.phone_verify(token)
                while cap_data == False:
                    logger.error(i18n_gt()["input_verify_fail"])
                    return self.get_token()
            elif risk["data"]["type"] == "sms":
                logger.warning(i18n_gt()["type_sms"])
                logger.warning(i18n_gt()["unsupport_sms"])
            elif risk["data"]["type"] == "biliword":
                logger.warning(i18n_gt()["type_sms"])
                logger.warning(i18n_gt()["unsupport_text"])
            else:
                logger.error(i18n_gt()["unknown_wind"])
                logger.warning(i18n_gt()["unsupport_captcha"])
            self.sdk.add_breadcrumb(
                category="gaia",
                message="Gaia passed",
                level="info",
            )
            return self.get_token()

    def generate_clickPosition(self) -> dict:
        """
        生成虚假的点击事件

        Returns:
            dict: 点击坐标和时间
        """
        # 生成随机的 x 和 y 坐标，以下范围大概是1920x1080屏幕下可能的坐标
        x = random.randint(1320, 1330)
        y = random.randint(880, 890)
        # 生成随机的起始时间和结束时间（或当前时间）
        now_timestamp = int(time.time() * 1000)
        # 添加一些随机时间差 (5s ~ 10s)
        origin_timestamp = now_timestamp - random.randint(5000, 10000)
        return {"x": x, "y": y, "origin": origin_timestamp, "now": now_timestamp}

    def create_order(self):
        url = "https://show.bilibili.com/api/ticket/order/createV2"
        data = {
            "project_id": self.config["project_id"],
            "screen_id": self.config["screen_id"],
            "sku_id": self.config["sku_id"],
            "token": self.token,
            "deviceId": "",
            "project_id": self.config["project_id"],
            "pay_money": self.config["all_price"],
            "count": self.config["count"],
            "timestamp": int(time.time() + 5),
            "order_type": self.config["order_type"],
            "newRisk": "true",
            "requestSource": "neul-next",
            "clickPosition": self.generate_clickPosition(),
        }
        if self.config["id_bind"] == 0:
            data["buyer"] = self.config["buyer"]
            data["tel"] = self.config["tel"]
        else:
            data["buyer_info"] = self.config["buyer_info"]
        if self.config["is_paper_ticket"]:
            data["deliver_info"] = self.config["deliver_info"]
        if "act_id" in self.config:
            data["act_id"] = self.config["act_id"]
        data["again"] = 1

        try:
            response = self.session.post(url, headers=self.headers, data=data)
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ):
            logger.error(i18n_gt()["network_timeout"])
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                            i18n_gt()["manual_change_ip"].format(
                                self.client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                self.session.close()
            return self.create_order()
        if response.status_code == 412:
            logger.error(i18n_gt()["wind_control"])
            logger.info(response.text)
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                            i18n_gt()["manual_change_ip"].format(
                                self.client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                self.session.close()
                return self.create_order()
            else:
                self.risk = True
                logger.error(i18n_gt()["pause_60s"])
                time.sleep(60)
                return {}
        return response.json()

    def fake_ticket(self, pay_token, order_id = None):
        url = (
            "https://show.bilibili.com/api/ticket/order/createstatus?project_id="
            + self.config["project_id"]
            + "&token="
            + pay_token
            + "&timestamp="
            + str(int(time.time() * 1000))
        )
        if order_id:
            url += "&orderId=" + str(order_id)
        logger.debug(url)
        response = self.session.get(url, headers=self.headers)
        if response.status_code == 412:
            logger.error(i18n_gt()["not_handled_412"])
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                            i18n_gt()["manual_change_ip"].format(
                                self.client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                self.session.close()
        response = response.json()
        logger.debug(response)
        if response["errno"] == 0:
            self.sdk.add_breadcrumb(
                category="success",
                message=f'Success, orderid:{response["data"]["order_id"]}, payurl:https://pay.bilibili.com/payplatform-h5/pccashier.html?params="{urllib.parse.quote(json.dumps(response["data"]["payParam"], ensure_ascii=False))}',
                level="info",
            )
            logger.success(i18n_gt()["pay_success"])
            order_id = response["data"]["order_id"]
            pay_url = response["data"]["payParam"]["code_url"]
            response["data"]["payParam"].pop("code_url")
            response["data"]["payParam"].pop("expire_time")
            response["data"]["payParam"].pop("pay_type")
            response["data"]["payParam"].pop("use_huabei")
            logger.info(i18n_gt()["bill_serial"] + order_id)
            self.order_id = order_id
            logger.info(i18n_gt()["bill_pay_hint"])
            logger.info(i18n_gt()["bill_qr"] + pay_url)
            qr = qrcode.QRCode()
            qr.add_data(pay_url)
            qr.print_ascii(invert=True)
            img = qr.make_image()
            img.show()
            logger.info(
                i18n_gt()["bill_open"] + " https://pay.bilibili.com/payplatform-h5/pccashier.html?params="
                + urllib.parse.quote(
                    json.dumps(response["data"]["payParam"], ensure_ascii=False)
                )
                + " " + i18n_gt()["bill_pay_ok"]
            )
            logger.info(i18n_gt()["bill_manual"])
            return True
        else:
            logger.error(i18n_gt()["bill_fail"])
            return False

    def order_status(self, order_id):
        url = "https://show.bilibili.com/api/ticket/order/info?order_id=" + str(order_id)
        response = self.session.get(url, headers=self.headers)
        if response.status_code == 412:
            logger.error(i18n_gt()["not_handled_412"])
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                            i18n_gt()["manual_change_ip"].format(
                                self.client.change_tps_ip(sign_type="hmacsha1")
                            )
                        )
                self.session.close()
        response = response.json()
        if response["data"]["status"] == 1:
            return True
        elif response["data"]["status"] == 2:
            logger.success(i18n_gt()["pay_ok"])
            return False
        elif response["data"]["status"] == 4:
            logger.warning(i18n_gt()["bill_cancel"])
            return False
        else:
            logger.warning(
                i18n_gt()["status_unknown"] + ": "
                + response["data"]["status_name"]
                + response["data"]["sub_status_name"]
            )
            return False

    def logout(self):
        #https://passport.bilibili.com/login/exit/v2
        url = "https://passport.bilibili.com/login/exit/v2"
        # biliCSRF	str	CSRF Token (位于 cookie 中的 bili_jct)
        response = self.session.post(url, headers=self.headers, data={
            "biliCSRF": self.headers["Cookie"][self.headers["Cookie"].index("bili_jct") + 9 : self.headers["Cookie"].index("bili_jct") + 41]
        }).json()
        if response["status"] == True:
            logger.success(i18n_gt()["quit_login"])
        else:
            logger.error(i18n_gt()["logout_fail"])

    def try_create_order(self):
        if not self.waited:
            logger.info(i18n_gt()["wait_4_96s"])
            time.sleep(4.96)
            self.waited = True
        result = self.create_order()
        if result == {}:
            return False
        if result["errno"] == 100009:
            logger.warning(i18n_gt()["ticketless"])
            self.waited = False
        elif result["errno"] == 100017:
            logger.warning(i18n_gt()["ticket_unbuyable"])
            self.waited = False
        elif result["errno"] == 3:
            logger.warning(i18n_gt()["slowdown_5s"])
        elif result["errno"] == 100001:
            logger.warning(i18n_gt()["bili_speed_limit"])
        elif result["errno"] == 100041:
            logger.warning(i18n_gt()["tokenless"])
        elif result["errno"] == 100016:
            logger.error(i18n_gt()["not_salable"])
        elif result["errno"] == 0:
            logger.success(i18n_gt()["bill_push_ok"])
            pay_token = result["data"]["token"]
            orderid = None
            if "orderId" in result["data"]:
                orderid = result["data"]["orderId"]
            if self.fake_ticket(pay_token, order_id = orderid):
                # self.logout()
                if "pushplus" in self.config:
                    # https://www.pushplus.plus/send/
                    url = "https://www.pushplus.plus/send"
                    response = requests.post(url, json={
                        "token": self.config["pushplus"],
                        "title": i18n_gt()["BHYG_notify"],
                        "content": i18n_gt()["rob_ok_paying"]+self.order_id,
                    }).json()
                    if response["code"] == 200:
                        logger.success(i18n_gt()["notify_ok"]+" "+response['data'])
                    else:
                        logger.error(i18n_gt()["notify_fail"]+" "+response)
                if "hunter" in self.config:
                    return True
                logger.info(i18n_gt()["unpaid_bill"])
                while self.order_status(self.order_id):
                    time.sleep(1)
                self.sdk.capture_message("Exit by in-app exit")
                return True
            else:
                logger.error(i18n_gt()["fake_ticket"])
        elif result["errno"] == 100051:
            self.token = self.get_token()
        elif result["errno"] == 100079 or result["errno"] == 100048:
            logger.info(result["msg"])
            logger.success(i18n_gt()["rob_already_ok"])
            self.sdk.capture_message("Exit by in-app exit")
            return True
        elif result["errno"] == 219:
            logger.info(i18n_gt()["ticket_sto_less"])
        else:
            logger.error(i18n_gt()["unknown_error"] + str(result))
        return False

    @staticmethod
    def gen_bili_ticket():

        def hmac_sha256(key, message):
            """
            使用HMAC-SHA256算法对给定的消息进行加密
            :param key: 密钥
            :param message: 要加密的消息
            :return: 加密后的哈希值
            """
            key = key.encode("utf-8")
            message = message.encode("utf-8")
            hmac_obj = hmac.new(key, message, hashlib.sha256)
            hash_value = hmac_obj.digest()
            hash_hex = hash_value.hex()
            return hash_hex

        o = hmac_sha256("XgwSnGZ1p", f"ts{int(time.time())}")
        url = "https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket"
        params = {
            "key_id": "ec02",
            "hexsign": o,
            "context[ts]": f"{int(time.time())}",
            "csrf": "",
        }

        headers = {
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0"
        }
        resp = requests.post(url, params=params, headers=headers).json()
        return resp["data"]["ticket"]
