import json
import os
import random
import requests
import time


######################
#### CONFIG AREA #####

project_id = ""
pay_money = -1 #真实应付价格
deviceId = "" #非必要
buy_time = int(time.mktime(time.strptime("2099-12-31 23:59:59", "%Y-%m-%d %H:%M:%S")))#发售刷新开始时间点，在此时可以开始疯狂刷新开售prepare了，请注意修改
cookie = ''
screen_id = ""
sku_id = ""
buyer_id = "" #以程序内的输入为准，如0,1

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
        "pay_money": pay_money,
        "order_type": "1",
        "timestamp": str(int(time.time()*1000)),
        "buyer_info": buyer_info,
        "token": token,
        "deviceId": deviceId,
        "clickPosition": '{"x":'+x+'"y":'+y+'"origin": '+str(int(time.time()*1000) - random.randint(1,100))+',"now": '+str(int(time.time()*1000))+'}',
    }
    response = requests.post(url, headers=headers, data=data)
    return response.json()

def get_token(screen_id,sku_id,project_id, count):
    global buy_time
    info = get_prepare(screen_id,sku_id,project_id, count)
    while(info == {}):
        print("[INFO] 未开放购票")
        if(int(time.time()) < buy_time):
            if buy_time == 4102415999:
                continue
            print("[INFO] 等待购票开放")
            time.sleep(buy_time - int(time.time()))
            print("[INFO] 开始购票")
            continue
        time.sleep(.1)
        info = get_prepare(screen_id,sku_id,project_id, count)
    if(info["shield"]["open"] == 0):
        print("[SUCCESS] 成功准备订单"+"https://show.bilibili.com/platform/confirmOrder.html?token="+info["token"])
        return info["token"]
    else:
        print("[INFO] 触发风控，打开："+str(info["shield"]))
        os.system("start "+info["shield"]['naUrl'])
        print("[INFO] 请手动完成验证")
        pause = input("完成验证后，按回车继续")
        return get_token(screen_id,sku_id,project_id, count)

if(__name__ == "__main__"):
    headers = {
            "Host": "show.bilibili.com",
            "Connection": "keep-alive",
            "Cookie": cookie,
            "Accept": "*/*",
            "Origin": "https://show.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        }
    if buy_time == 4102415999:
        print("[WARNING] 未设置购票时间")
    if(cookie == ""):
        cookie = input("请输入cookie：")
    if(project_id == "" or screen_id == "" or sku_id == "" or pay_money == -1):
        if(project_id == ""):
            project_id = input("请输入项目id：")
        ids = get_ids(project_id)
        screen_id,sku_id,pay_money = ids.split(" ")
    buyer_info = get_buyer_info()
    count = len(json.loads(buyer_info))
    token=get_token(screen_id,sku_id,project_id, count)
    print("[INFO] 开始下单")
    while(1):
        result = create_order(screen_id,sku_id,token,deviceId,project_id,pay_money, count)
        if(result["errno"] == 100009):
            print(".",end="",flush=True)
        elif(result["errno"] == 100001):
            print("[ERROR] 触发风控")
        elif(result["errno"] == 0):
            print("[SUCCESS] 成功下单，锁票成功！请在5分钟内完成支付操作")
            pay_token = result["data"]["token"]
            print("[INFO] 请打开链接或在手机上完成支付")
            pause = input("按回车继续")
        elif(result["errno"] == 100051):
            token=get_token(screen_id,sku_id,project_id, count)
        else:
            print("[ERROR] "+str(result))
        time.sleep(.1)
