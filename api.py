import json
import random
import time
import urllib.parse
import hashlib
import hmac

import qrcode
import requests
from loguru import logger


class BilibiliHyg:
    def __init__(self, config, sdk,client,session):
        self.waited = False
        self.sdk = sdk
        self.config = config
        self.config["gaia_vtoken"] = None
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BHYG/0.7.0",
        }

        self.headers["Cookie"] = self.config["cookie"]

        self.client = client
        self.session = session
        if self.client != None:
            self.ip = self.client.tps_current_ip(sign_type="hmacsha1")
        logger.info("准备完毕，获取token中...")
        self.token = self.get_token()
        logger.info("即将开始下单")

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
            logger.error("网络连接超时")
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                        "手动切换，当前IP为："
                        + self.client.change_tps_ip(sign_type="hmacsha1")
                    )
                self.session.close()
                return self.get_ticket_status()
            return -1, 0
        try:
            if response.status_code == 412:
                logger.error(
                    "可能被业务风控\n该种业务风控请及时暂停，否则可能会引起更大问题。"
                )
                if self.config["proxy"]:
                    if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                        logger.info(
                            "手动切换，当前IP为："
                            + self.client.change_tps_ip(sign_type="hmacsha1")
                        )
                    self.session.close()
                    return self.get_ticket_status()
                else:
                    self.risk = True
                    logger.error("暂停30s")
                    logger.error(
                        "你也可以尝试更换网络环境，如重启流量（飞行模式开关）重新拨号（重启光猫）等"
                    )
                    time.sleep(30)
                    return -1, 0
            screens = response.json()["data"]["screen_list"]
            # 找到 字段id为screen_id的screen
            screen = {}
            for i in range(len(screens)):
                if screens[i]["id"] == int(self.config["screen_id"]):
                    screen = screens[i]
                    break
            if screen == {}:
                logger.error("未找到场次")
                return -1, 0
            # 找到 字段id为sku_id的sku
            skus = screen["ticket_list"]
            sku = {}
            for i in range(len(skus)):
                if skus[i]["id"] == int(self.config["sku_id"]):
                    sku = skus[i]
                    break
            if sku == {}:
                logger.error("未找到票档")
                return -1, 0
            return int(sku["sale_flag_number"]), sku["clickable"]
        except:
            logger.error("可能被风控")
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
            "order_type": "1",
            "count": self.config["count"],
            "sku_id": self.config["sku_id"],
            "token": "",
            "newRisk": "true",
            "requestSource": "neul-next",
        }
        response = self.session.post(url, headers=self.headers, data=data)
        if response.status_code == 412:
            logger.error("被412风控，请联系作者")
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                        "手动切换，当前IP为："
                        + self.client.change_tps_ip(sign_type="hmacsha1")
                    )
                self.session.close()
                return self.get_prepare()
        if response.json()["errno"] != 0 and response.json()["errno"] != -401:
            logger.error(response.json()["msg"])
        return response.json()["data"]

    def verify(self, gt, challenge, token):
        from geetest import run
        self.captcha_data = run(gt, challenge, token)
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
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f)
        return success

    def get_token(self):
        info = self.get_prepare()
        if info == {}:
            logger.warning("未开放购票或被风控，请检查配置问题，休息1s")
            # time.sleep(1)
            self.get_token()
        if info["token"]:
            logger.success(
                "成功准备订单"
                + "https://show.bilibili.com/platform/confirmOrder.html?token="
                + info["token"]
            )
            self.sdk.add_breadcrumb(
                category="prepare",
                message=f'Order prepared as token:{info["token"]}',
                level="info",
            )
            return info["token"]
        else:
            logger.warning("触发风控。")
            logger.warning("类型：验证码 ")
            self.sdk.add_breadcrumb(
                category="gaia",
                message="Gaia found",
                level="info",
            )
            riskParam = info["ga_data"]["riskParams"]
            # https://api.bilibili.com/x/gaia-vgate/v1/register
            gtest = self.session.post(
                "https://api.bilibili.com/x/gaia-vgate/v1/register",
                headers=self.headers,
                data=riskParam,
            ).json()
            while gtest["code"] != 0:
                gtest = self.session.post(
                    "https://api.bilibili.com/x/gaia-vgate/v1/register",
                    headers=self.headers,
                    data=riskParam,
                ).json()
            gt, challenge, token = (
                gtest["data"]["geetest"]["gt"],
                gtest["data"]["geetest"]["challenge"],
                gtest["data"]["token"],
            )
            cap_data = self.verify(gt, challenge, token)
            while cap_data == False:
                logger.error("验证失败，请重新验证")
                return self.get_token()
            logger.info("验证成功")
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
            "order_type": "1",
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

        if self.config["again"]:
            data["again"] = 1

        try:
            response = self.session.post(url, headers=self.headers, data=data)
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ):
            logger.error("网络连接超时")
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                        "手动切换，当前IP为："
                        + self.client.change_tps_ip(sign_type="hmacsha1")
                    )
                self.session.close()
            return self.create_order()
        if response.status_code == 412:
            logger.error(
                "可能被业务风控\n该种业务风控请及时暂停，否则可能会引起更大问题。"
            )
            logger.info(response.text)
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                        "手动切换，当前IP为："
                        + self.client.change_tps_ip(sign_type="hmacsha1")
                    )
                self.session.close()
                return self.create_order()
            else:
                self.risk = True
                logger.error("暂停60s")
                time.sleep(60)
                return {}
        return response.json()

    def fake_ticket(self, pay_token, order_id):
        url = (
            "https://show.bilibili.com/api/ticket/order/createstatus?project_id="
            + self.config["project_id"]
            + "&token="
            + pay_token
            + "&timestamp="
            + str(int(time.time() * 1000))
            + "&orderId="
            + str(order_id)
        )
        response = self.session.get(url, headers=self.headers)
        if response.status_code == 412:
            logger.error("被412风控，请联系作者")
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                        "手动切换，当前IP为："
                        + self.client.change_tps_ip(sign_type="hmacsha1")
                    )
                self.session.close()
        response = response.json()
        if response["errno"] == 0:
            self.sdk.add_breadcrumb(
                category="success",
                message=f'Success, orderid:{response["data"]["order_id"]}, payurl:https://pay.bilibili.com/payplatform-h5/pccashier.html?params="{urllib.parse.quote(json.dumps(response["data"]["payParam"], ensure_ascii=False))}',
                level="info",
            )
            logger.success("成功购票")
            order_id = response["data"]["order_id"]
            pay_url = response["data"]["payParam"]["code_url"]
            response["data"]["payParam"].pop("code_url")
            response["data"]["payParam"].pop("expire_time")
            response["data"]["payParam"].pop("pay_type")
            response["data"]["payParam"].pop("use_huabei")
            logger.info("订单号：" + order_id)
            self.order_id = order_id
            logger.info("请在微信/支付宝/QQ中扫描以下二维码，完成支付")
            logger.info("二维码内容：" + pay_url)
            qr = qrcode.QRCode()
            qr.add_data(pay_url)
            qr.print_ascii(invert=True)
            img = qr.make_image()
            img.show()
            logger.info(
                "或打开 https://pay.bilibili.com/payplatform-h5/pccashier.html?params="
                + urllib.parse.quote(
                    json.dumps(response["data"]["payParam"], ensure_ascii=False)
                )
                + " 完成支付"
            )
            logger.info("请手动完成支付")
            return True
        else:
            logger.error("购票失败")
            return False

    def order_status(self, order_id):
        url = "https://show.bilibili.com/api/ticket/order/info?order_id=" + order_id
        response = self.session.get(url, headers=self.headers)
        if response.status_code == 412:
            logger.error("被412风控，请联系作者")
            if self.config["proxy"]:
                if self.ip == self.client.tps_current_ip(sign_type="hmacsha1"):
                    logger.info(
                        "手动切换，当前IP为："
                        + self.client.change_tps_ip(sign_type="hmacsha1")
                    )
                self.session.close()
        response = response.json()
        if response["data"]["status"] == 1:
            return True
        elif response["data"]["status"] == 2:
            logger.success("订单支付成功，祝您游玩愉快！")
            return False
        elif response["data"]["status"] == 4:
            logger.warning("订单已取消")
            return False
        else:
            logger.warning(
                "当前状态未知: "
                + response["data"]["status_name"]
                + response["data"]["sub_status_name"]
            )
            return False

    def try_create_order(self):
        result = self.create_order()
        if result == {}:
            return False
        if result["errno"] == 100009:
            logger.warning("无票")
            self.waited = False
        elif result["errno"] == 100017:
            logger.warning("票种不可售")
            self.waited = False
        elif result["errno"] == 3:
            logger.warning("慢一点（强制5秒）")
            if not self.waited:
                logger.info("等待4.9秒")
                time.sleep(4.9)
                self.waited = True
        elif result["errno"] == 100001:
            logger.warning("小电视速率限制")
        elif result["errno"] == 100041:
            logger.warning("不是，哥们，你token呢？")
        elif result["errno"] == 100016:
            logger.error("项目不可售")
        elif result["errno"] == 0:
            logger.success("成功尝试下单！正在检测是否为假票")
            pay_token = result["data"]["token"]
            orderid = result["data"]["orderId"]
            if self.fake_ticket(pay_token, orderid):
                while self.order_status(self.order_id):
                    logger.info("订单未支付，正在等待")
                    time.sleep(3)
                self.sdk.capture_message("Exit by in-app exit")
                return True
            else:
                logger.error("假票，继续抢票")
        elif result["errno"] == 100051:
            self.token = self.get_token()
        elif result["errno"] == 100079 or result["errno"] == 100048:
            logger.success("已经抢到了啊喂！")
            self.sdk.capture_message("Exit by in-app exit")
            return True
        else:
            logger.error("未知错误:" + str(result))
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
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        }
        resp = requests.post(url, params=params, headers=headers).json()
        return resp["data"]["ticket"]