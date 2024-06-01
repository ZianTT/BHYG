import json
import random
import time
import requests
from loguru import logger
import qrcode
import urllib.parse
import json
import random
import time

class BilibiliHyg:
        def __init__(self, config, sdk):
            common_project_id = []
            self.waited = False
            self.sdk = sdk
            self.config = config
            self.config["gaia_vtoken"] = None
            self.session = requests.Session()
            self.headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BHYG/0.6.3",
            }
            
            self.headers["Cookie"] = self.config["cookie"]

            if "co_delay" not in self.config:
                co_delay = input("请输入创建订单时间间隔(该选项影响412风控概率，单开建议使用0)(秒)：")
                try:
                    self.config["co_delay"] = float(co_delay)
                except:
                    logger.warning("未设置时间间隔，默认为0")
                    self.config["co_delay"] = 0
                while(self.config["co_delay"] < 0):
                    logger.error("时间间隔过短")
                    self.config["co_delay"] = float(input("请输入创建订单时间间隔(该选项影响412风控概率，单开建议使用0)(秒)："))
            if "status_delay" not in self.config:
                try:
                    self.config["status_delay"] = float(input("请输入票务信息检测时间间隔(该选项影响412风控概率)(秒)："))
                except:
                    logger.warning("未设置时间间隔，默认为0.2")
                    self.config["status_delay"] = 0.2
                while(self.config["status_delay"] < 0):
                    logger.error("时间间隔过短")
                    self.config["status_delay"] = float(input("请输入票务信息检测时间间隔(该选项影响412风控概率)(秒)："))
            
            if "project_id" not in self.config or "screen_id" not in self.config or "sku_id" not in self.config or "pay_money" not in self.config or "id_bind" not in self.config:
                while True:
                    logger.info("常用项目id如下：")
                    for i in range(len(common_project_id)):
                        logger.info(common_project_id[i]["name"]+common_project_id[i]["id"])
                    if len(common_project_id) == 0:
                        logger.info("暂无")
                    self.config["project_id"] = input("请输入项目id：")
                    url = "https://show.bilibili.com/api/ticket/project/getV2?version=134&id="+self.config["project_id"]
                    response = self.session.get(url, headers=self.headers)
                    if response.status_code == 412:
                            logger.error("被412风控，请联系作者")
                    response = response.json()
                    if(response["errno"] == 3):
                        logger.error("未找到项目ID")
                        continue
                    if(response["data"] == {}):
                        logger.error("服务器无返回")
                        continue
                    if(response["data"]["is_sale"] == 0):
                        logger.error("项目不可售")
                        continue
                    break
                logger.info("项目名称："+response["data"]["name"])
                self.config["id_bind"] = response["data"]["id_bind"]
                self.config["is_paper_ticket"] = response["data"]["has_paper_ticket"]
                screens = response["data"]["screen_list"]
                for i in range(len(screens)):
                    logger.info(str(i)+". "+screens[i]["name"])
                while True:
                    try:
                        screen_id = int(input("请输入场次序号："))
                        if screen_id >= len(screens):
                            raise ValueError
                        break
                    except ValueError:
                        logger.error("序号错误")
                tickets = screens[int(screen_id)]["ticket_list"] # type: ignore
                for i in range(len(tickets)):
                    logger.info(str(i)+". "+tickets[i]["desc"]+" "+str(tickets[i]["price"]/100)+"元")
                while True:
                    try:
                        sku_id = int(input("请输入票档序号："))
                        if sku_id >= len(tickets):
                            raise ValueError
                        break
                    except ValueError:
                        logger.error("序号错误")
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
                    resp_ticket = self.session.get(url, headers=self.headers)
                    if(resp_ticket.status_code == 412):
                        logger.error("被412风控，请联系作者")
                    addr_list = resp_ticket.json()["data"]["addr_list"]
                    if len(addr_list) == 0:
                        logger.error("没有收货地址，请先添加收货地址")
                    else:
                        for i in range(len(addr_list)):
                            logger.info(f"{str(i)}. {addr_list[i]['prov']+addr_list[i]['city']+addr_list[i]['area']+addr_list[i]['addr']} {addr_list[i]['name']} {addr_list[i]['phone']}")
                        while True:
                            try:
                                addr_index = int(input("请选择收货地址序号："))
                                if addr_index >= len(addr_list):
                                    raise ValueError
                                break
                            except ValueError:
                                logger.error("序号错误")
                        addr = addr_list[addr_index]
                        self.config["deliver_info"] = json.dumps({
                            "name" : addr["name"],
                            "tel" : addr["phone"],
                            "addr_id" : addr["addr"],
                            "addr" : addr["prov"]+addr["city"]+addr["area"]+addr["addr"],
                        },ensure_ascii=False)
                logger.debug("您的screen_id 和 sku_id 和 pay_money 分别为："+self.config["screen_id"]+" "+self.config["sku_id"]+" "+self.config["pay_money"])
            self.token = ""
            if self.config["id_bind"] != 0 and ("buyer_info" not in self.config):
                url = "https://show.bilibili.com/api/ticket/buyer/list"
                response = self.session.get(url, headers=self.headers)
                if response.status_code == 412:
                    logger.error("被412风控，请联系作者")
                buyer_infos = response.json()["data"]["list"]
                self.config["buyer_info"] = []
                if len(buyer_infos) == 0:
                    logger.error("未找到购票人，请前往实名添加购票人")
                else:
                    multiselect = True
                    if(self.config["id_bind"] == 1):
                        logger.info("本项目只能购买一人票")
                        multiselect = False
                    while True:
                        try:
                            if multiselect:
                                for i in range(len(buyer_infos)):
                                    logger.info(f"{str(i)}. {buyer_infos[i]['name']} {buyer_infos[i]['personal_id']} {buyer_infos[i]['tel']}")
                                buyerids = input("请选择购票人序号(多人用空格隔开)：").split(" ")
                                self.config["buyer_info"] = []
                                for select in buyerids:
                                    self.config["buyer_info"].append(buyer_infos[int(select)]) # type: ignore
                                    logger.info("已选择购票人"+buyer_infos[int(select)]["name"]) # type: ignore
                            else:
                                for i in range(len(buyer_infos)):
                                    logger.info(f"{str(i)}. {buyer_infos[i]['name']} {buyer_infos[i]['personal_id']} {buyer_infos[i]['tel']}")
                                index = int(input("请选择购票人序号："))
                                self.config["buyer_info"].append(buyer_infos[index])
                                logger.info("已选择购票人"+buyer_infos[index]["name"])
                            break
                        except:
                            logger.error("序号错误")
                    if "count" not in self.config:
                        self.config["count"] = len(self.config["buyer_info"])
                    self.config["buyer_info"] = json.dumps(self.config["buyer_info"])
            if self.config["id_bind"] == 0 and ("buyer" not in self.config or "tel" not in self.config):
                logger.info("请添加联系人信息")
                self.config["buyer"] = input("联系人姓名：")
                while True:
                    self.config["tel"] = input("联系人手机号：")
                    if len(self.config["tel"]) == 11:
                        break
                    logger.error("手机号长度错误")
                if "count" not in self.config:
                    self.config["count"] = input("请输入票数：")
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
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(self.config, f)
            self.sdk.capture_message('config complete')
            logger.info("准备完毕，获取token中...")
            self.token = self.get_token()
            logger.info("即将开始下单")
            

        def get_ticket_status(self):
            url = "https://show.bilibili.com/api/ticket/project/getV2?version=134&id="+self.config["project_id"]
            try:
                response = self.session.get(url, headers=self.headers, timeout=1)
            except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
                logger.error("网络连接超时")
                return -1, 0
            try:
                if response.status_code == 412:
                    logger.error("可能被业务风控\n该种业务风控请及时暂停，否则可能会引起更大问题。")
                    self.risk = True
                    logger.error("暂停30s")
                    logger.error("你也可以尝试更换网络环境，如重启流量（飞行模式开关）重新拨号（重启光猫）等")
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
                return int(sku["sale_flag_number"]),sku["clickable"]
            except:
                logger.error("可能被风控")
                return -1, 0
        
        def get_prepare(self):
            url = "https://show.bilibili.com/api/ticket/order/prepare?project_id="+self.config["project_id"]
            if self.config["gaia_vtoken"]:
                url += "&gaia_vtoken="+self.config["gaia_vtoken"]
            data = {
                "project_id": self.config["project_id"],
                "screen_id": self.config["screen_id"],
                "order_type": "1",
                "count": self.config["count"],
                "sku_id": self.config["sku_id"],
                "token": "",
                "newRisk": "true",
                "requestSource": "pc-new",
            }
            response = self.session.post(url, headers=self.headers, data=data)
            if response.status_code == 412:
                logger.error("被412风控，请联系作者")
            if(response.json()["errno"] != 0 and response.json()["errno"] != -401):
                logger.error(response.json()["msg"])
            return response.json()["data"]

        def verify(self,gt,challenge,token):
            self.pending_captcha = {
                "gt": gt,
                "challenge": challenge,
                "token": token
            }
            with open("data/toc", "w") as f:
                f.write(json.dumps({"type":"geetest","data":self.pending_captcha}))
            with open("data/tos", "a+") as f:
                while True:
                    f.seek(0,0)
                    data = f.read()
                    if data != "":
                        self.captcha_data = json.loads(data)
                        if self.captcha_data["success"] == False:
                            f.truncate(0)
                            return False
                        self.captcha_data["csrf"] = self.headers["Cookie"][self.headers["Cookie"].index("bili_jct") + 9:self.headers["Cookie"].index("bili_jct") + 41]
                        self.captcha_data["token"] = token
                        success = self.session.post("https://api.bilibili.com/x/gaia-vgate/v1/validate", headers=self.headers, data=self.captcha_data).json()["data"]["is_valid"]
                        self.config["gaia_vtoken"] = token
                        self.captcha_data = None
                        if self.headers["Cookie"].find("x-bili-gaia-vtoken") != -1:
                            self.headers["Cookie"] = self.headers["Cookie"].split("; x-bili-gaia-vtoken")[0]
                        self.headers["Cookie"] += "; x-bili-gaia-vtoken="+ token
                        f.truncate(0)
                        with open("config.json", "w", encoding="utf-8") as f:
                            json.dump(self.config, f)
                        return success

        def get_token(self):
            info = self.get_prepare()
            if(info == {}):
                logger.warning("未开放购票或被风控，请检查配置问题，休息1s")
                time.sleep(1)
                self.get_token()
            if(info["token"]):
                logger.success("成功准备订单"+"https://show.bilibili.com/platform/confirmOrder.html?token="+info["token"])
                self.sdk.add_breadcrumb(
                    category='prepare',
                    message=f'Order prepared as token:{info["token"]}',
                    level='info',
                )
                return info["token"]
            else:
                logger.warning("触发风控。")
                logger.warning("类型：验证码 ")
                self.sdk.add_breadcrumb(
                    category='gaia',
                    message='Gaia found',
                    level='info',
                )
                riskParam=info["ga_data"]["riskParams"]
                #https://api.bilibili.com/x/gaia-vgate/v1/register
                gtest=self.session.post("https://api.bilibili.com/x/gaia-vgate/v1/register",headers=self.headers, data=riskParam).json()
                while(gtest["code"]!=0):
                    gtest=self.session.post("https://api.bilibili.com/x/gaia-vgate/v1/register",headers=self.headers, data=riskParam).json()
                gt, challenge, token = gtest['data']['geetest']['gt'], gtest['data']['geetest']['challenge'], gtest['data']['token']
                cap_data = self.verify(gt, challenge, token)
                while cap_data == False:
                    logger.error("验证失败，请重新验证")
                    return self.get_token()
                logger.info("验证成功")
                self.sdk.add_breadcrumb(
                    category='gaia',
                    message='Gaia passed',
                    level='info',
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
            return {
                "x": x,
                "y": y,
                "origin": origin_timestamp,
                "now": now_timestamp
            }
        
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
                "timestamp": int(time.time()+5),
                "order_type": "1",
                "newRisk": "true",
                "requestSource": "pc-new",
                "clickPosition": self.generate_clickPosition()
            }
            if self.config["id_bind"] == 0:
                data["buyer"] = self.config["buyer"]
                data["tel"] = self.config["tel"]
            else:
                data["buyer_info"] = self.config["buyer_info"]
            if self.config["is_paper_ticket"]:
                data["deliver_info"] = self.config["deliver_info"]

            response = self.session.post(url, headers=self.headers, data=data)
            if response.status_code == 412:
                logger.error("可能被业务风控\n该种业务风控请及时暂停，否则可能会引起更大问题。")
                self.risk = True
                logger.error("暂停60s")
                time.sleep(60)
                return {}
            return response.json()

        def fake_ticket(self, pay_token):
            url = "https://show.bilibili.com/api/ticket/order/createstatus?project_id="+self.config["project_id"]+"&token="+pay_token+"&timestamp="+str(int(time.time()*1000))
            response = self.session.get(url, headers=self.headers)
            if response.status_code == 412:
                logger.error("被412风控，请联系作者")
            response = response.json()
            if response["errno"] == 0:
                self.sdk.add_breadcrumb(
                    category='success',
                    message=f'Success, orderid:{response["data"]["order_id"]}, payurl:https://pay.bilibili.com/payplatform-h5/pccashier.html?params="{urllib.parse.quote(json.dumps(response["data"]["payParam"],ensure_ascii=False))}',
                    level='info',
                )
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
                img = qr.make_image()
                img.show()
                logger.info("或打开 https://pay.bilibili.com/payplatform-h5/pccashier.html?params="+urllib.parse.quote(json.dumps(response["data"]["payParam"],ensure_ascii=False))+" 完成支付")
                logger.info("请手动完成支付")
                return True
            else:
                logger.error("购票失败")
                return False
            
        def order_status(self,order_id):
            url = "https://show.bilibili.com/api/ticket/order/info?order_id="+order_id
            response = self.session.get(url, headers=self.headers)
            if response.status_code == 412:
                logger.error("被412风控，请联系作者")
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
                logger.warning("当前状态未知: "+response["data"]["status_name"]+response["data"]["sub_status_name"])
                return False
        def try_create_order(self):
            result = self.create_order()
            if(result == {}):
                return False
            if(result["errno"] == 100009):
                logger.warning("无票")
                self.waited = False
            elif(result["errno"] == 3):
                logger.warning("慢一点（强制5秒）")
                if not self.waited:
                    logger.info("等待4.9秒")
                    time.sleep(4.9)
                    self.waited = True
            elif(result["errno"] == 100001):
                logger.warning("小电视速率限制")
            elif(result["errno"] == 100016):
                logger.error("项目不可售")
            elif(result["errno"] == 0):
                logger.success("成功尝试下单！正在检测是否为假票")
                pay_token = result["data"]["token"]
                if(self.fake_ticket(pay_token)):
                    while self.order_status(self.order_id):
                        logger.info("订单未支付，正在等待")
                        time.sleep(3)
                    self.sdk.capture_message('Exit by in-app exit')
                    return True
                else:
                    logger.error("假票，继续抢票")
            elif(result["errno"] == 100051):
                self.token = self.get_token()
            elif(result["errno"] == 100079 or result["errno"] == 100048):
                logger.success("已经抢到了啊喂！")
                self.sdk.capture_message('Exit by in-app exit')
                return True
            else:
                logger.error("未知错误:"+str(result))
            return False