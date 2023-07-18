# Copyright (c) 2023 ZianTT
# bilibili-hyg is licensed under Mulan PubL v2.
# You can use this software according to the terms and conditions of the Mulan PubL v2.
# You may obtain a copy of Mulan PubL v2 at:
#          http://license.coscl.org.cn/MulanPubL-2.0
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PubL v2 for more details.

import requests
import json
import time

class BilibiliHyg:
    def __init__(self, easy_mode=-1, watcher_mode=-1, cookie="", riskheader="", project_id="", screen_id="", sku_id="", pay_money=-1, buyer_id=""):
        self.easy_mode = easy_mode
        self.watcher_mode = watcher_mode
        self.cookie = cookie
        self.riskheader = riskheader
        self.project_id = project_id
        self.screen_id = screen_id
        self.sku_id = sku_id
        self.pay_money = pay_money
        self.buyer_id = buyer_id
        self.buyer_info = []
        self.buyer = ""
        self.tel = ""
        if self.easy_mode == -1:
            easy_mode_yn = input("是否开启简易模式？（y/n）")
            if(easy_mode_yn == "y"):
                self.easy_mode = True
            elif(easy_mode_yn == "n"):
                self.easy_mode = False
            else:
                print("[ERROR] 请输入y或n")
                exit()
        if(self.watcher_mode == -1):
            watcher_mode_yn = input("是否开启仅检测模式？（y/n）")
            if(watcher_mode_yn == "y"):
                self.watcher_mode = True
            elif(watcher_mode_yn == "n"):
                self.watcher_mode = False
            else:
                print("[ERROR] 请输入y或n")
                exit()
        if(not self.watcher_mode and self.cookie == ""):
            self.cookie = input("请输入cookie：").encode("utf-8")
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
            self.buyer, self.tel = self.get_contact_info()
            self.token = self.get_token()
        print("[INFO] 开始下单")

    def get_ticket_status(self):
        url = "https://show.bilibili.com/api/ticket/project/get?version=134&id="+self.project_id
        try:
            response = requests.get(url, headers=self.headers, timeout=1)
        except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout):
            print("[ERROR] 网络连接超时")
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
                print("[ERROR] 未找到场次")
                return -1, 0
            # 找到 字段id为sku_id的sku
            skus = screen["ticket_list"]
            sku = {}
            for i in range(len(skus)):
                if skus[i]["id"] == int(self.sku_id):
                    sku = skus[i]
                    break
            if sku == {}:
                print("[ERROR] 未找到票档")
                return -1, 0
            return int(sku["sale_flag_number"]),int(sku["num"])
        except:
            print("[ERROR] 可能被风控")
            return -1, 0

    def test_risk(self):
        url = "https://show.bilibili.com/api/ticket/order/createV2"
        result = requests.get(url, headers=self.headers).status_code
        if(result == 412):
            return False
        else:
            return True

    def get_ids(self):
        url = "https://show.bilibili.com/api/ticket/project/get?version=134&id="
        response = requests.get(url+self.project_id, headers=self.headers)
        screens = response.json()["data"]["screen_list"]
        screen_id = screens[0]["id"]
        skus = screens[0]["ticket_list"]
        sku_id = skus[0]["id"]
        pay_money = skus[0]["price"]
        return str(screen_id), str(sku_id), str(pay_money)

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
            print("[INFO] 未找到购票人，请前往实名添加购票人，或留空则代表不传入购票人信息，请确保该展支持非实名购票。")
        else:
            print("[INFO] 请选择购票人，留空则代表不传入购票人信息，请确保该展支持非实名购票。")
        if self.buyer_id == "":
            self.buyer_id = input("请输入购票人序号：")
        if(self.buyer_id != ""):
            buyerids = self.buyer_id.split(",")
            self.buyer_info = []
            for i in range(len(buyerids)):
                self.buyer_info.append(buyer_infos[int(buyerids[i])])
                print("[INFO] 已选择购票人"+buyer_infos[int(buyerids[i])]["name"])
        else:
            print("[INFO] 已选择不传入购票人信息")
            self.buyer_info = [0]
        return json.dumps(self.buyer_info)

    def get_contact_info(self):
        print("[INFO] 若该展为非实名购票，请传入信息，留空则不传入")
        buyer = input("请输入姓名：")
        tel = input("请输入手机号：")
        return buyer, tel

    def get_token(self):
        url = "https://show.bilibili.com/api/ticket/order/prepare?project_id="+self.project_id
        data = {
            "project_id": self.project_id,
            "screen_id": self.screen_id,
            "sku_id": self.sku_id,
            "project_id": self.project_id,
            "order_type": "1",
            "count": self.count
        }
        response = requests.post(url, headers=self.headers, data=data)
        return response.json()["data"]["token"]

    def create_order(self):
        url = "https://show.bilibili.com/api/ticket/order/createV2"
        data = {
            "screen_id": self.screen_id,
            "sku_id": self.sku_id,
            "token": self.token,
            "deviceId": "",
            "project_id": self.project_id,
            "pay_money": self.pay_money,
            "count": self.count
        }
        if self.riskheader != "":
            data["risk_header"] = self.riskheader
        if self.buyer_info != "":
            data["buyer_info"] = self.buyer_info
        if self.buyer != "":
            data["buyer"] = self.buyer
        if self.tel != "":
            data["tel"] = self.tel
        response = requests.post(url, headers=self.headers, data=data)
        return response.json()

    def run(self):
        reset = 0
        while(1):
            if reset > 800 and not self.watcher_mode:
                self.token = self.get_token()
                reset = 0
            status, num = self.get_ticket_status()
            if(status == 2 or num >= 1):
                print("[INFO] 剩余票数："+str(num))
                if self.watcher_mode:
                    time.sleep(1)
                    continue
                for i in range(20):
                    try:
                        result = self.create_order()
                    except:
                        print("[ERROR] 可能被业务风控")
                        print("该种业务风控请及时暂停，否则可能会引起更大问题。")
                        print("开始检测是否解除风控")
                        risk = True
                        while(risk):
                            time.sleep(120)
                            if(self.test_risk()):
                                risk = False
                                print("已解除风控")
                                break
                            else:
                                print("风控未解除")
                        continue
                    if(result["errno"] == 100009):
                        if(self.easy_mode):
                            print("。",end="",flush=True)
                        else:
                            print("[INFO]无票")
                    elif(result["errno"] == 0):
                        print(result)
                        print("[SUCCESS] 成功下单！请在10分钟内完成支付操作")
                        print("[INFO] 近期假票较多，可能并非真实抢到，请注意查看订单情况")
                        pay_token = result["data"]["token"]
                        print("[INFO] 请打开链接或在手机上完成支付")
                    elif(result["errno"] == 100051):
                        self.token = self.get_token()
                    elif(result["errno"] == 100079):
                        print("[SUCCESS] 你是真抢到了，我先停了，你直接退出就好")
                        time.sleep(100000)
                    else:
                        print("[ERROR] "+str(result))
                    time.sleep(.3)
                    reset += 2
            elif(status == 1):
                print("[INFO] 未开放购票")
            elif(status == 8):
                if(self.easy_mode):
                    print("’",end="",flush=True)
                else:
                    print("[INFO] 暂时售罄，即将放票")
            elif(status == 4):
                if(self.easy_mode):
                    print("”",end="",flush=True)
                else:
                    print("[INFO] 已售罄")
            elif(status == -1):
                continue
            else:
                print("[ERROR] "+str(status))
            time.sleep(.3)
            reset += 2

if __name__ == "__main__":
    bilibili_hyg = BilibiliHyg()
    bilibili_hyg.run()
