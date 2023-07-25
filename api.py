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
from loguru import logger
logger.info("开始检测运行环境")
try:
    import requests
except ImportError:
    logger.error("未安装requests库")
    logger.info("程序将在5秒内退出")
    time.sleep(5)
    exit()

class BilibiliHyg:
    def __init__(self, easy_mode="-1", watcher_mode="-1", cookie="", riskheader="", project_id="", screen_id="", sku_id="", pay_money="-1", buyer_id="", buyer="", tel=""):
        self.easy_mode = int(easy_mode)
        self.watcher_mode = int(watcher_mode)
        self.cookie = cookie
        self.riskheader = riskheader
        self.project_id = project_id
        self.screen_id = screen_id
        self.sku_id = sku_id
        self.pay_money = int(pay_money)
        self.buyer_id = buyer_id
        self.buyer_info = []
        self.buyer = buyer
        self.tel = tel
        if self.easy_mode == -1:
            easy_mode_yn = input("是否开启简易模式？（y/n）")
            if(easy_mode_yn == "y"):
                self.easy_mode = True
            elif(easy_mode_yn == "n"):
                self.easy_mode = False
            else:
                logger.error("请输入y或n")
                logger.info("程序将在5秒内退出")
                time.sleep(5)
                exit()
        if(self.watcher_mode == -1):
            watcher_mode_yn = input("是否开启仅检测模式？（y/n）")
            if(watcher_mode_yn == "y"):
                self.watcher_mode = True
            elif(watcher_mode_yn == "n"):
                self.watcher_mode = False
            else:
                logger.error("请输入y或n")
                logger.info("程序将在5秒内退出")
                time.sleep(5)
                exit()
        if(not self.watcher_mode and self.cookie == ""):
            self.cookie = input("请输入cookie：").encode("utf-8")
        if(not self.watcher_mode):
            auth = self.get_auth()
            if(not auth):
                logger.info("登录失败，请检查cookie是否正确")
                logger.info("程序将在5秒内退出")
                time.sleep(5)
                exit()           
        self.headers = {
            "Host": "show.bilibili.com",
            "Connection": "keep-alive",
            "Cookie": self.cookie,
            "Accept": "*/*",
            "Origin": "https://show.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        }
        if self.riskheader != "":
            self.headers["X-Risk-Header"] = self.riskheader
        if self.project_id == "" or self.screen_id == "" or self.sku_id == "" or self.pay_money == -1:
            if self.project_id == "":
                self.project_id = input("请输入项目id：")
            self.screen_id, self.sku_id, self.pay_money = self.get_ids()
        self.count = 0
        self.token = ""
        if not self.watcher_mode:
            self.buyer_info = self.get_buyer_info()
            self.count = len(json.loads(self.buyer_info))
            self.get_contact_info()
            self.token = self.get_token()
        logger.info("开始下单")
    
    def get_auth(self):
        user = requests.get("https://api.bilibili.com/x/web-interface/nav", headers={"cookie": self.cookie})
        user = user.json()
        if(user["data"]["isLogin"]):
            print("用户 "+user["data"]["uname"]+" 登录成功")
            return True
        else:
            print("登录失败")
            return False

    def get_ticket_status(self):
        url = "https://show.bilibili.com/api/ticket/project/get?version=134&id="+self.project_id
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
                if screens[i]["id"] == int(self.screen_id):
                    screen = screens[i]
                    break
            if screen == {}:
                logger.error("未找到场次")
                return -1, 0
            # 找到 字段id为sku_id的sku
            skus = screen["ticket_list"]
            sku = {}
            for i in range(len(skus)):
                if skus[i]["id"] == int(self.sku_id):
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

    def get_ids(self):
        url = "https://show.bilibili.com/api/ticket/project/get?version=134&id="+self.project_id
        response = requests.get(url).json()
        screens = response["data"]["screen_list"]
        for i in range(len(screens)):
            print("["+str(i)+"] "+screens[i]["name"])
        screen_id = input("请输入场次序号：")
        tickets = screens[int(screen_id)]["ticket_list"]
        for i in range(len(tickets)):
            print("["+str(i)+"] "+tickets[i]["desc"]+" "+str(tickets[i]["price"]/100)+"元")
        sku_id = input("请输入票档序号：")
        ids = str(screens[int(screen_id)]["id"])+" "+str(tickets[int(sku_id)]["id"])+" "+str(tickets[int(sku_id)]["price"])
        logger.info("您的screen_id 和 sku_id 和 pay_money 分别为："+ids)
        return str(screens[int(screen_id)]["id"]),str(tickets[int(sku_id)]["id"]),str(tickets[int(sku_id)]["price"])

    def get_buyer_info(self):
        url = "https://show.bilibili.com/api/ticket/buyer/list"
        response = requests.get(url, headers=self.headers)
        buyer_infos = response.json()["data"]["list"]
        self.buyer_info = []
        for i in range(len(buyer_infos)):
            print("["+str(i)+"] "+buyer_infos[i]["name"]+" "+buyer_infos[i]["personal_id"]+" "+buyer_infos[i]["tel"])
            if(buyer_infos[i]["is_default"] == 1):
                self.buyer_info = [buyer_infos[i]]
        if(len(self.buyer_info) == 0):
            logger.info("未找到购票人，请前往实名添加购票人，或留空则代表不传入购票人信息，请确保该展支持非实名购票。")
        else:
            logger.info("请选择购票人，留空则代表不传入购票人信息，请确保该展支持非实名购票。")
        if self.buyer_id == "":
            self.buyer_id = input("请输入购票人序号：")
        if(self.buyer_id != "" and self.buyer_id != "-1"):
            buyerids = self.buyer_id.split(",")
            self.buyer_info = []
            for i in range(len(buyerids)):
                self.buyer_info.append(buyer_infos[int(buyerids[i])])
                logger.info("已选择购票人"+buyer_infos[int(buyerids[i])]["name"])
        else:
            logger.info("已选择不传入购票人信息")
            self.buyer_info = [0]
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
        url = "https://show.bilibili.com/api/ticket/order/prepare?project_id="+self.project_id
        data = {
            "project_id": self.project_id,
            "screen_id": self.screen_id,
            "order_type": "1",
            "count": self.count,
            "sku_id": self.sku_id,
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
            logger.info("请在浏览器中打开以下链接，完成验证")
            logger.info(info["shield"]['naUrl'])
            webbrowser.open(info["shield"]['naUrl'])
            logger.info("请手动完成验证")
            pause = input("完成验证后，按回车继续")
            return self.get_token()

    def create_order(self):
        url = "https://show.bilibili.com/api/ticket/order/createV2"
        data = {
            "screen_id": self.screen_id,
            "sku_id": self.sku_id,
            "token": self.token,
            "deviceId": "",
            "project_id": self.project_id,
            "pay_money": int(self.pay_money)*int(self.count),
            "count": self.count
        }
        if self.riskheader != "":
            data["risk_header"] = self.riskheader
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
        url = "https://show.bilibili.com/api/ticket/order/createstatus?project_id="+self.project_id+"&token="+pay_token+"&timestamp="+str(int(time.time()*1000))
        response = requests.get(url, headers=self.headers).json()
        if response["errno"] == 0:
            logger.success("成功购票")
            order_id = response["data"]["order_id"]
            pay_url = response["data"]["payParam"]["code_url"]
            logger.info("订单号："+order_id)
            logger.info("请扫描弹出的二维码，完成支付")
            qrcode.make(pay_url).show()
            logger.info("请手动完成支付")
            return True
        else:
            logger.error("购票失败")
            return False

    def run(self):
        reset = 0
        while(1):
            if reset > 800 and not self.watcher_mode:
                self.token = self.get_token()
                reset = 0
            if reset % 100 == 0:
                self.risk = self.test_risk()
            if self.risk:
                status = -1
            status, num = self.get_ticket_status()
            if(status == 2 or num >= 1):
                logger.info("剩余票数："+str(num))
                if self.watcher_mode:
                    time.sleep(1)
                    continue
                for i in range(20):
                    result = self.create_order()
                    if(result == {}):
                        continue
                    if(result["errno"] == 100009):
                        if(self.easy_mode):
                            print("。",end="",flush=True)
                        else:
                            logger.info("无票")
                    elif(result["errno"] == 100001):
                        if(self.easy_mode):
                            print("，",end="",flush=True)
                        else:
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
                if(self.easy_mode):
                    print("’",end="",flush=True)
                else:
                    logger.info("暂时售罄，即将放票")
            elif(status == 4):
                if(self.easy_mode):
                    print("”",end="",flush=True)
                else:
                    logger.info("已售罄")
            elif(status == -1):
                continue
            else:
                logger.error("未知状态:"+str(status))
            time.sleep(.3)
            reset += 2