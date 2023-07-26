# Copyright (c) 2023 ZianTT
# bilibili-hyg is licensed under Mulan PubL v2.
# You can use this software according to the terms and conditions of the Mulan PubL v2.
# You may obtain a copy of Mulan PubL v2 at:
#          http://license.coscl.org.cn/MulanPubL-2.0
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PubL v2 for more details.
import json
import os
import time
from loguru import logger
import requests
from pick import pick
from login import login
from captcha.hyg_geetest import verify

class HygException(Exception):
    pass

class BilibiliHyg:
    def __init__(self, config):
        self.config = config
        self.buyer_info = []
        self.config["cookie"] = login()
        self.headers = {
            "Host": "show.bilibili.com",
            "Connection": "keep-alive",
            "Cookie": self.config["cookie"],
            "Accept": "*/*",
            "Origin": "https://show.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        }
        self.config["project_id"] = input("请输入项目id：")
        self.config["screen_id"], self.config["sku_id"], self.config["pay_money"] = self.get_ids()
        self.count = 0
        self.token = ""
        self.buyer_info = self.get_buyer_info()
        self.count = len(json.loads(self.buyer_info))
        #self.get_contact_info()
        self.token = self.get_token()
        logger.info("即将开始下单")

    def get_ticket_status(self):
        url = "https://show.bilibili.com/api/ticket/project/get?version=134&id="+self.config["project_id"]
        try:
            response = requests.get(url, headers=self.headers, timeout=1)
        except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout):
            logger.error("网络连接超时")
            return -1, 0
        try:
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
            return int(sku["sale_flag_number"]),int(sku["num"])
        except:
            logger.error("可能被风控")
            return -1, 0

    def test_risk(self):
        url = "https://show.bilibili.com/api/ticket/order/createV2"
        result = requests.get(url, headers=self.headers).status_code
        if(result == 412):
            return False
        else:
            return True

    def get_ids(self):
        url = "https://show.bilibili.com/api/ticket/project/get?version=134&id="+self.config["project_id"]
        response = requests.get(url).json()
        screens = response["data"]["screen_list"]
        screen_id = pick([screen["name"] for screen in screens], "请选择场次：")[1]
        tickets = screens[int(screen_id)]["ticket_list"] # type: ignore
        sku_id = pick([ticket["desc"]+" "+str(ticket["price"]/100)+"元" for ticket in tickets], "请选择票档：")[1]

        ids = str(screens[int(screen_id)]["id"])+" "+str(tickets[int(sku_id)]["id"])+" "+str(tickets[int(sku_id)]["price"]) # type: ignore
        logger.info("您的screen_id 和 sku_id 和 pay_money 分别为："+ids)
        return str(screens[int(screen_id)]["id"]),str(tickets[int(sku_id)]["id"]),str(tickets[int(sku_id)]["price"]) # type: ignore

    def get_buyer_info(self):
        url = "https://show.bilibili.com/api/ticket/buyer/list"
        response = requests.get(url, headers=self.headers)
        buyer_infos = response.json()["data"]["list"]
        self.buyer_info = []
        if(len(buyer_infos) == 0):
            logger.info("未找到购票人，请前往实名添加购票人")
        else:
            logger.info("请选择购票人，留空则代表不传入购票人信息，请确保该展支持非实名购票。")

            buyerids = pick([buyer_infos[i]["name"]+" "+buyer_infos[i]["personal_id"]+" "+buyer_infos[i]["tel"] for i in range(len(buyer_infos))], "请选择购票人：", multiselect=True, min_selection_count=1)
            self.buyer_info = []
            for select in buyerids:
                self.buyer_info.append(buyer_infos[select[1]]) # type: ignore
                logger.info("已选择购票人"+buyer_infos[select[1]]["name"]) # type: ignore
        return json.dumps(self.buyer_info)

    def get_contact_info(self):
        logger.info("若该展为非实名购票，请传入信息，留空则不传入")
        if self.buyer == "":
            self.buyer = input("请输入姓名：")
        if self.tel == "":
            self.tel = input("请输入手机号：")
        if(self.buyer == "" or self.buyer == "-1"):
            self.buyer = "-1"
        if(self.tel == "" or self.tel == "-1"):
            self.tel = "-1"
        return
    
    def get_prepare(self):
        url = "https://show.bilibili.com/api/ticket/order/prepare?project_id="+self.config["project_id"]
        data = {
            "project_id": self.config["project_id"],
            "screen_id": self.config["screen_id"],
            "order_type": "1",
            "count": self.count,
            "sku_id": self.config["sku_id"],
            "token": ""
        }
        response = requests.post(url, headers=self.headers, data=data)
        if(response.json()["errno"] != 0):
            print("[ERROR] "+response.json()["msg"])
        return response.json()["data"]
    
    def get_token(self):
        info = self.get_prepare()
        while(info == {}):
            logger.info("未开放购票")
            time.sleep(.5)
            info = self.get_prepare()
        if(info["shield"]["open"] == 0):
            logger.success("成功准备订单"+"https://show.bilibili.com/platform/confirmOrder.html?token="+info["token"])
            return info["token"]
        else:
            logger.info("触发风控。")
            logger.info("类型：验证码 "+info["shield"]['verifyMethod'])
            # logger.info("请在浏览器中打开以下链接，完成验证")
            # logger.info(info["shield"]['naUrl'])
            # os.system("start "+info["shield"]['naUrl'])
            # logger.info("请手动完成验证")
            # pause = input("完成验证后，按回车继续")
            voucher = info["shield"]['voucher']
            # 若返回不为true，则持续验证
            while(not verify(self.config["cookie"],voucher)):
                continue
            return self.get_token()

    def create_order(self):
        url = "https://show.bilibili.com/api/ticket/order/createV2"
        data = {
            "screen_id": self.config["screen_id"],
            "sku_id": self.config["sku_id"],
            "token": self.token,
            "deviceId": "",
            "project_id": self.config["project_id"],
            "pay_money": int(self.config["pay_money"])*int(self.count),
            "count": self.count
        }
        # if self.riskheader != "":
        #     data["risk_header"] = self.riskheader
        if self.buyer_info != "":
            data["buyer_info"] = self.buyer_info
        if self.buyer != "-1":
            data["buyer"] = self.buyer
        if self.tel != "-1":
            data["tel"] = self.tel
        response = requests.post(url, headers=self.headers, data=data)
        if(response.status_code == 412):
            logger.error("可能被业务风控\n该种业务风控请及时暂停，否则可能会引起更大问题。")
            self.risk = True
            return {}
        return response.json()

    def fake_ticket(self, pay_token):
        url = "https://show.bilibili.com/api/ticket/order/createstatus?project_id="+self.config["project_id"]+"&token="+pay_token+"&timestamp="+str(int(time.time()*1000))
        response = requests.get(url, headers=self.headers).json()
        if response["errno"] == 0:
            logger.success("成功购票")
            order_id = response["data"]["order_id"]
            pay_url = response["data"]["payParam"]["code_url"]
            logger.info("订单号："+order_id)
            logger.info("请在浏览器中打开以下链接，完成支付")
            logger.info(pay_url)
            os.system("start "+pay_url)
            logger.info("请手动完成支付")
            return True
        else:
            logger.error("购票失败")
            return False

    def run(self):
        reset = 0
        while(1):
            if reset > 800 and not self.config["watcher_mode"]:
                self.token = self.get_token()
                reset = 0
            if reset % 100 == 0:
                self.risk = self.test_risk()
            if self.risk:
                status = -1
            status, num = self.get_ticket_status()
            if(status == 2 or num >= 1):
                logger.info("剩余票数："+str(num))
                if self.config["watcher_mode"]:
                    time.sleep(1)
                    continue
                for i in range(20):
                    result = self.create_order()
                    if(result == {}):
                        continue
                    if(result["errno"] == 100009):
                        logger.info("无票")
                    elif(result["errno"] == 100001):
                        logger.info("小电视速率限制")
                    elif(result["errno"] == 0):
                        logger.success("成功尝试下单！正在检测是否为假票")
                        pay_token = result["data"]["token"]
                        if(self.fake_ticket(pay_token)):
                            pause = input("请确认是否已经支付，按回车继续")
                            logger.info("程序将在5秒内退出")
                            time.sleep(5)
                            exit()
                        else:
                            logger.error("假票，继续抢票")
                    elif(result["errno"] == 100051):
                        self.token = self.get_token()
                    elif(result["errno"] == 100079):
                        logger.success("已经抢到了啊喂！")
                        logger.info("程序将在5秒内退出")
                        time.sleep(5)
                        exit()
                    else:
                        logger.error("未知错误:"+str(result))
                    reset += 2
            elif(status == 1):
                logger.info("未开放购票")
            elif(status == 8):
                logger.info("暂时售罄，即将放票")
            elif(status == 4):
                logger.info("已售罄")
            elif(status == -1):
                continue
            else:
                logger.error("未知状态:"+str(status))
            time.sleep(.3)
            reset += 2