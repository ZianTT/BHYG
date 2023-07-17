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
import random
import requests
import time


######################
#### CONFIG AREA #####

project_id = ""
pay_money = -1 #此处应填入票种单价，会自动计算
deviceId = "" #非必要
cookie = ''
screen_id = ""
sku_id = ""
buyer_id = "" #以程序内的输入为准，如0,1
riskheader = "" #非必要，用于风控验证
easy_mode = -1 #简易模式，只显示某些符号，防止重要信息被忽略。
watcher_mode = -1 #监视模式，不执行抢票操作

######################
    
def get_ids(project_id):
    url = "https://show.bilibili.com/api/ticket/project/get?version=134&id="+project_id
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
    print("[INFO]您的screen_id 和 sku_id 和 pay_money 分别为："+ids)
    return ids

def get_buyer_info():
    global buyer_id
    url = "https://show.bilibili.com/api/ticket/buyer/list"
    response = requests.get(url, headers=headers)
    buyer_infos = response.json()["data"]["list"]
    buyer_info = [buyer_infos[0]]
    for i in range(len(buyer_infos)):
        print("["+str(i)+"] "+buyer_infos[i]["name"]+" "+buyer_infos[i]["personal_id"]+" "+buyer_infos[i]["tel"])
        if(buyer_infos[i]["is_default"] == 1):
            buyer_info = [buyer_infos[i]]
    print("[INFO] 请选择购票人，默认"+buyer_info[0]["name"])
    if buyer_id == "":
        buyer_id = input("请输入购票人序号：")
    if(buyer_id != ""):
        buyerids = buyer_id.split(",")
        buyer_info = []
        for i in range(len(buyerids)):
            buyer_info.append(buyer_infos[int(buyerids[i])])
            print("[INFO] 已选择购票人"+buyer_infos[int(buyerids[i])]["name"])
    return json.dumps(buyer_info)

def get_prepare(screen_id,sku_id,project_id, count):
    global headers
    url = "https://show.bilibili.com/api/ticket/order/prepare?project_id="+project_id
    data = {
        "project_id": project_id,
        "screen_id": screen_id,
        "order_type": "1",
        "count": count,
        "sku_id": sku_id,
        "token": ""
    }
    response = requests.post(url, headers=headers, data=data)
    if(response.json()["errno"] != 0):
        print("[ERROR] "+response.json()["msg"])
    return response.json()["data"]

def create_order(screen_id,sku_id,token,deviceId,project_id,pay_money, count):
    global headers
    url = "https://show.bilibili.com/api/ticket/order/createV2?project_id="+project_id
    x = str(1223+random.randint(0,10)-5)
    y = str(653+random.randint(0,10)-5)
    data = {
        "project_id": project_id,
        "screen_id": screen_id,
        "sku_id": sku_id,
        "count": count,
        "pay_money": pay_money*count,
        "order_type": "1",
        "timestamp": str(int(time.time()*1000)),
        "buyer_info": buyer_info,
        "token": token,
        "deviceId": deviceId,
        "clickPosition": '{"x":'+x+'"y":'+y+'"origin": '+str(int(time.time()*1000) - random.randint(1,100))+',"now": '+str(int(time.time()*1000))+'}',
    }
    try:
        response = requests.post(url, headers=headers, data=data, timeout=1)
    except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout):
        print("[ERROR] 请求超时")
        return create_order(screen_id,sku_id,token,deviceId,project_id,pay_money, count)
    if(response.json()["errno"] == 100001):
        if(easy_mode):
            print("，",end="",flush=True)
        else:
            print("[INFO] 速率限制中（小电视）")
    return response.json()

def get_token(screen_id,sku_id,project_id, count):
    info = get_prepare(screen_id,sku_id,project_id, count)
    while(info == {}):
        print("[INFO] 未开放购票")
        time.sleep(.5)
        info = get_prepare(screen_id,sku_id,project_id, count)
    if(info["shield"]["open"] == 0):
        print("[SUCCESS] 成功准备订单"+"https://show.bilibili.com/platform/confirmOrder.html?token="+info["token"])
        return info["token"]
    else:
        print("[INFO] 触发风控。")
        print("[INFO] 类型：验证码 "+info["shield"]['verifyMethod'])
        print("[INFO] 请在浏览器中打开以下链接，完成验证")
        print("[INFO] "+info["shield"]['naUrl'])
        os.system("start "+info["shield"]['naUrl'])
        print("[INFO] 请手动完成验证")
        pause = input("完成验证后，按回车继续")
        return get_token(screen_id,sku_id,project_id, count)

def get_ticket_status(screen_id,sku_id,project_id):
    global headers
    url = "https://show.bilibili.com/api/ticket/project/get?version=134&id="+project_id
    try:
        response = requests.get(url, headers=headers, timeout=1)
    except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout):
        print("[ERROR] 网络连接超时")
        return -1, 0
    try:
        screens = response.json()["data"]["screen_list"]
        # 找到 字段id为screen_id的screen
        screen = {}
        for i in range(len(screens)):
            if screens[i]["id"] == int(screen_id):
                screen = screens[i]
                break
        if screen == {}:
            print("[ERROR] 未找到场次")
            return -1, 0
        # 找到 字段id为sku_id的sku
        skus = screen["ticket_list"]
        sku = {}
        for i in range(len(skus)):
            if skus[i]["id"] == int(sku_id):
                sku = skus[i]
                break
        if sku == {}:
            print("[ERROR] 未找到票档")
            return -1, 0
        return int(sku["sale_flag_number"]),int(sku["num"])
    except:
        print("[ERROR] 可能被风控")
        return -1, 0
    
def test_risk():
    url = "https://show.bilibili.com/api/ticket/order/createV2"
    result = requests.get(url, headers=headers).status_code
    if(result == 412):
        return False
    else:
        return True

if(__name__ == "__main__"):
    if easy_mode == -1:
        easy_mode_yn = input("是否开启简易模式？（y/n）")
        if(easy_mode_yn == "y"):
            easy_mode = True
        elif(easy_mode_yn == "n"):
            easy_mode = False
        else:
            print("[ERROR] 请输入y或n")
            exit()
    if(watcher_mode == -1):
        watcher_mode_yn = input("是否开启仅检测模式？（y/n）")
        if(watcher_mode_yn == "y"):
            watcher_mode = True
        elif(watcher_mode_yn == "n"):
            watcher_mode = False
        else:
            print("[ERROR] 请输入y或n")
            exit()
    if(not watcher_mode and cookie == ""):
        cookie = input("请输入cookie：").encode("utf-8")
    headers = {
            "Host": "show.bilibili.com",
            "Connection": "keep-alive",
            "Cookie": cookie,
            "Accept": "*/*",
            "Origin": "https://show.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        }
    if riskheader != "":
        headers["X-Risk-Header"] = riskheader
    if(project_id == "" or screen_id == "" or sku_id == "" or pay_money == -1):
        if(project_id == ""):
            project_id = input("请输入项目id：")
        ids = get_ids(project_id)
        screen_id,sku_id,pay_money = ids.split(" ")
    count = 0
    token = ""
    if not watcher_mode:
        buyer_info = get_buyer_info()
        count = len(json.loads(buyer_info))
        token=get_token(screen_id,sku_id,project_id, count)
    print("[INFO] 开始下单")
    reset = 0
    while(1):
        if reset > 800 and not watcher_mode:
            token=get_token(screen_id,sku_id,project_id, count)
            reset = 0
        status, num = get_ticket_status(screen_id,sku_id,project_id) # type: ignore
        if(not watcher_mode and status == 2 or num >= 1):
            print("[INFO] 剩余票数："+str(num))
            for i in range(20):
                try:
                    result = create_order(screen_id,sku_id,token,deviceId,project_id,pay_money, count)
                except:
                    print("[ERROR] 可能被业务风控")
                    print("该种业务风控请及时暂停，否则可能会引起更大问题。")
                    print("开始检测是否解除风控")
                    risk = True
                    while(risk):
                        time.sleep(120)
                        if(test_risk()):
                            risk = False
                            print("已解除风控")
                            break
                        else:
                            print("风控未解除")
                    continue
                if(result["errno"] == 100009):
                    if(easy_mode):
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
                    token=get_token(screen_id,sku_id,project_id, count)
                else:
                    print("[ERROR] "+str(result))
            reset += 10
        elif(status == 1):
            print("[INFO] 未开放购票")
        elif(status == 8):
            if(easy_mode):
                print("’",end="",flush=True)
            else:
                print("[INFO] 暂时售罄，即将放票")
        elif(status == 4):
            if(easy_mode):
                print("”",end="",flush=True)
            else:
                print("[INFO] 已售罄")
        elif(status == -1):
            continue
        else:
            print("[ERROR] "+str(status))
        time.sleep(.3)
        reset += 2
        
