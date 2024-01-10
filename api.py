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
import webbrowser
import qrcode
import time
from urllib.parse import quote, urlencode
from loguru import logger
import qrcode
import requests
from pick import pick
from login import login
from captcha.hyg_geetest import verify

def exit():
    os._exit(0)

class HygException(Exception):
    pass

class BilibiliHyg:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        }
        # 若无该数组执行
        if "cookie" not in self.config:
            self.config["cookie"] = login()
        self.headers["Cookie"] = self.config["cookie"]
        
        if "project_id" not in self.config or "screen_id" not in self.config or "sku_id" not in self.config or "pay_money" not in self.config or "id_bind" not in self.config:
            self.config["project_id"] = input("请输入项目id：")
            url = "https://show.bilibili.com/api/ticket/project/getV2?version=134&id="+self.config["project_id"]
            response = requests.get(url, headers=self.headers)
            if response.status_code == 412:
                    logger.error("被412风控，请联系作者")
            response = response.json()
            self.config["id_bind"] = response["data"]["id_bind"]
            self.config["is_paper_ticket"] = response["data"]["has_paper_ticket"]
            screens = response["data"]["screen_list"]
            screen_id = pick([screen["name"] for screen in screens], "请选择场次：")[1]
            tickets = screens[int(screen_id)]["ticket_list"] # type: ignore
            sku_id = pick([ticket["desc"]+" "+str(ticket["price"]/100)+"元" for ticket in tickets], "请选择票档：")[1]
            
            self.config["screen_id"] = str(screens[int(screen_id)]["id"])
            self.config["sku_id"] = str(tickets[int(sku_id)]["id"])
            self.config["pay_money"] = str(tickets[int(sku_id)]["price"])
            self.config["ticket_desc"] = str(tickets[int(sku_id)]["desc"])
            if self.config["is_paper_ticket"]:
                if response["data"]["express_free_flag"]:
                    self.config["express_fee"] = 0
                else:
                    self.config["express_fee"] = response["data"]["express_fee"]
                url = "https://show.bilibili.com/api/ticket/addr/list"
                resp_ticket = requests.get(url, headers=self.headers)
                if(resp_ticket.status_code == 412):
                    logger.error("被412风控，请联系作者")
                addr_list = resp_ticket.json()["data"]["addr_list"]
                if len(addr_list) == 0:
                    logger.error("没有收货地址，请先添加收货地址")
                else:
                    addr = addr_list[int(pick([addr["prov"]+addr["city"]+addr["area"]+addr["addr"]+" "+addr["name"]+" "+addr["phone"] for addr in addr_list], "请选择收货地址：")[1])]
                    self.config["deliver_info"] = json.dumps({
                        "name" : addr["name"],
                        "tel" : addr["phone"],
                        "addr_id" : addr["addr"],
                        "addr" : addr["prov"]+addr["city"]+addr["area"]+addr["addr"],
                    },ensure_ascii=False)
            logger.debug("您的screen_id 和 sku_id 和 pay_money 分别为："+self.config["screen_id"]+" ",self.config["sku_id"]+" ",self.config["pay_money"])
        self.token = ""
        if self.config["id_bind"] != 0 and ("buyer_info" not in self.config):
            url = "https://show.bilibili.com/api/ticket/buyer/list"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 412:
                logger.error("被412风控，请联系作者")
            buyer_infos = response.json()["data"]["list"]
            self.config["buyer_info"] = []
            if len(buyer_infos) == 0:
                logger.info("未找到购票人，请前往实名添加购票人")
            else:
                multiselect = True
                if(self.config["id_bind"] == 1):
                    logger.info("本项目只能购买一人票")
                    multiselect = False
                buyerids = pick([buyer_infos[i]["name"]+" "+buyer_infos[i]["personal_id"]+" "+buyer_infos[i]["tel"] for i in range(len(buyer_infos))],
                                "请选择购票人：",
                                multiselect=multiselect,
                                min_selection_count=1)
                self.config["buyer_info"] = []
                for select in buyerids:
                    self.config["buyer_info"].append(buyer_infos[select[1]]) # type: ignore
                    logger.info("已选择购票人"+buyer_infos[select[1]]["name"]) # type: ignore
                if "count" not in self.config:
                    self.config["count"] = len(self.config["buyer_info"])
                self.config["buyer_info"] = json.dumps(self.config["buyer_info"])
        if self.config["id_bind"] == 0 and ("buyer" not in self.config or "tel" not in self.config):
            logger.info("请添加联系人信息")
            self.config["buyer"] = input("联系人姓名：")
            self.config["tel"] = input("联系人手机号：")
            if "count" not in self.config:
                self.config["count"] = input("请输入票数：")
        self.token = self.get_token()
        if self.config["is_paper_ticket"]:
            if self.config["express_fee"] == 0:
                self.config["all_price"] = int(self.config['pay_money'])*int(self.config['count'])
                logger.info(f"共 {self.config['count']} 张 {self.config['ticket_desc']} 票，单张价格为 {int(self.config['pay_money'])/100}，纸质票，邮费免去，总价为{self.config['all_price'] / 100}")
            else:
                self.config["all_price"] = int(self.config['pay_money'])*int(self.config['count'])+self.config['express_fee']
                logger.info(f"共 {self.config['count']} 张 {self.config['ticket_desc']} 票，单张价格为 {int(self.config['pay_money'])/100}，纸质票，邮费为 {self.config['express_fee'] / 100}，总价为{self.config['all_price'] / 100}")
        else:
            self.config["all_price"] = int(self.config['pay_money'])*int(self.config['count'])
            logger.info(f"共 {self.config['count']} 张 {self.config['ticket_desc']} 票，单张价格为 {int(self.config['pay_money'])/100}，总价为{self.config['all_price'] / 100}")
        with open("config.py", "w", encoding="utf-8") as f:
            f.write(str(self.config))
        logger.info("即将开始下单")

    def get_ticket_status(self):
        url = "https://show.bilibili.com/api/ticket/project/getV2?version=134&id="+self.config["project_id"]
        try:
            response = requests.get(url, headers=self.headers, timeout=1)
        except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout):
            logger.error("网络连接超时")
            return -1, 0
        try:
            if response.status_code == 412:
                logger.error("被412风控，请联系作者")
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
            return int(sku["sale_flag_number"]),int(sku["num"])
        except:
            logger.error("可能被风控")
            return -1, 0

    def test_risk(self):
        url = "https://show.bilibili.com/api/ticket/order/createV2"
        result = requests.post(url, headers=self.headers).status_code
        if(result == 412):
            return False
        else:
            return True
    
    def get_prepare(self):
        url = "https://show.bilibili.com/api/ticket/order/prepare?project_id="+self.config["project_id"]
        data = {
            "project_id": self.config["project_id"],
            "screen_id": self.config["screen_id"],
            "order_type": "1",
            "count": self.config["count"],
            "sku_id": self.config["sku_id"],
            "token": ""
        }
        response = requests.post(url, headers=self.headers, data=data)
        if response.status_code == 412:
            logger.error("被412风控，请联系作者")
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
            logger.info("验证链接 "+info["shield"]['naUrl'])
            # os.system("start "+info["shield"]['naUrl'])
            logger.info("正在尝试自动验证...")
            # pause = input("完成验证后，按回车继续")
            voucher = info["shield"]['voucher']
            # 若返回不为true，则持续验证
            while(not verify(self.config["cookie"],voucher)):
                continue
            logger.info("验证成功")
            return self.get_token()

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
            "timestamp": int(time.time()),
        }
        if self.config["id_bind"] == 0:
            data["buyer"] = self.config["buyer"]
            data["tel"] = self.config["tel"]
        else:
            data["buyer_info"] = self.config["buyer_info"]
        if self.config["is_paper_ticket"]:
            data["deliver_info"] = self.config["deliver_info"]

        response = requests.post(url, headers=self.headers, data=data)
        if response.status_code == 412:
            logger.error("可能被业务风控\n该种业务风控请及时暂停，否则可能会引起更大问题。")
            self.risk = True
            return {}
        return response.json()

    def fake_ticket(self, pay_token):
        url = "https://show.bilibili.com/api/ticket/order/createstatus?project_id="+self.config["project_id"]+"&token="+pay_token+"&timestamp="+str(int(time.time()*1000))
        response = requests.get(url, headers=self.headers)
        if response.status_code == 412:
            logger.error("被412风控，请联系作者")
        response = response.json()
        if response["errno"] == 0:
            logger.success("成功购票")
            order_id = response["data"]["order_id"]
            pay_url = response["data"]["payParam"]["code_url"]
            response["data"]["payParam"].pop("code_url")
            response["data"]["payParam"].pop("expire_time")
            response["data"]["payParam"].pop("pay_type")
            response["data"]["payParam"].pop("use_huabei")
            logger.info("订单号："+order_id)
            self.order_id = order_id
            logger.info("请在微信/支付宝/QQ中扫描以下二维码，完成支付")
            logger.info("二维码内容："+pay_url)
            qr = qrcode.QRCode()
            qr.add_data(pay_url)
            qr.print_ascii(invert=True)
            logger.info("或打开 https://pay.bilibili.com/payplatform-h5/pccashier.html?params="+quote(json.dumps(response["data"]["payParam"],ensure_ascii=False))+" 完成支付")
            logger.info("请手动完成支付")
            return True
        else:
            logger.error("购票失败")
            return False
        
    def order_status(self,order_id):
        url = "https://show.bilibili.com/api/ticket/order/info?order_id="+order_id
        response = requests.get(url, headers=self.headers)
        if response.status_code == 412:
            logger.error("被412风控，请联系作者")
        response = response.json()
        if response["data"]["status"] == 1:
            return True
        elif response["data"]["status"] == 2:
            logger.success("订单支付成功，祝您游玩愉快！")
            return False
        elif response["data"]["status"] == 4:
            logger.info("订单已取消")
            return False
        else:
            logger.info("当前状态未知: "+response["data"]["status_name"]+response["data"]["sub_status_name"])
            return False


    def run(self):
        reset = 0
        while(1):
            if reset > 800:
                self.token = self.get_token()
                reset = 0
            if reset % 100 == 0:
                self.risk = self.test_risk()
            if self.risk:
                status = -1
            status, num = self.get_ticket_status()
            if(status == 2 or num >= 1):
                logger.info("剩余票数："+str(num))
                if(status == 1):
                    logger.warning("未开放购票")
                elif(status == 3):
                    logger.warning("已停售")
                    if not "ignore" in vars():
                        ignore = input("当前状态可能无法抢票，请确认是否继续抢票，按回车继续")
                elif(status == 5):
                    logger.warning("不可售")
                    if not "ignore" in vars():
                        ignore = input("当前状态可能无法抢票，请确认是否继续抢票，按回车继续")
                for i in range(20):
                    result = self.create_order()
                    if(result == {}):
                        continue
                    if(result["errno"] == 100009):
                        logger.info("无票")
                    elif(result["errno"] == 100001):
                        logger.info("小电视速率限制")
                    elif(result["errno"] == 100016):
                        logger.error("项目不可售")
                    elif(result["errno"] == 0):
                        logger.success("成功尝试下单！正在检测是否为假票")
                        pay_token = result["data"]["token"]
                        if(self.fake_ticket(pay_token)):
                            while self.order_status(self.order_id):
                                logger.info("订单未支付，正在等待")
                                time.sleep(3)
                            exit()
                        else:
                            logger.error("假票，继续抢票")
                    elif(result["errno"] == 100051):
                        self.token = self.get_token()
                    elif(result["errno"] == 100079 or result["errno"] == 100048):
                        logger.success("已经抢到了啊喂！")
                        logger.info("程序将在5秒内退出")
                        time.sleep(5)
                        exit()
                    else:
                        logger.error("未知错误:"+str(result))
                    reset += 2
            elif(status == 1):
                logger.warning("未开放购票")
            elif(status == 3):
                logger.warning("已停售")
            elif(status == 4):
                logger.info("已售罄")
            elif(status == 5):
                logger.warning("不可售")
            elif(status == 6):
                logger.error("免费票，程序尚未适配")
                logger.info("程序将在5秒内退出")
                time.sleep(5)
                exit()
            elif(status == 8):
                logger.info("暂时售罄，即将放票")
            
            elif(status == -1):
                continue
            else:
                logger.error("未知状态:"+str(status))
            time.sleep(.3)
            reset += 2