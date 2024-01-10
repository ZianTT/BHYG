'''
Author: ZianTT 2508164094@qq.com
Date: 2023-07-25 17:08:39
LastEditors: ZianTT 2508164094@qq.com
LastEditTime: 2023-12-18 00:04:21
FilePath: \bilibili-hyg\login.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import time
import requests
import requests.utils
import qrcode
import os

def exit():
    os._exit(0)

def login():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        }

    session = requests.session()

    session.get("https://www.bilibili.com/", headers=headers)

    def getCookies(cookie_jar, domain):
        cookie_dict = cookie_jar.get_dict(domain=domain)
        found = ['%s=%s' % (name, value) for (name, value) in cookie_dict.items()]
        return ';'.join(found)


    generate = session.get("https://passport.bilibili.com/x/passport-login/web/qrcode/generate", headers=headers)
    generate = generate.json()
    if generate['code'] == 0:
        url = generate['data']['url']
    else:
        print(generate)
        exit()
        return
    qr = qrcode.QRCode()
    qr.add_data(url)
    qr.print_ascii(invert=True)
    print("请使用Bilibili手机客户端扫描二维码")
    while True:
        time.sleep(1)
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll?source=main-fe-header&qrcode_key="+generate['data']['qrcode_key']
        req = session.get(url, headers=headers)
        # read as utf-8
        check = req.json()["data"]
        if check['code'] == 0:
            print("登录成功")
            cookies = requests.utils.dict_from_cookiejar(session.cookies)
            break
        elif check['code'] == 86101:
            pass
        elif check['code'] == 86090:
            print(check["message"])
        elif check['code'] == 86083:
            print(check["message"])
            exit()
        elif check['code'] == 86038:
            print(check["message"])
            exit()
        else:
            print(check)
            exit()
    lst = []
    for item in cookies.items():
        lst.append(f"{item[0]}={item[1]}")

    cookie_str = ';'.join(lst)
    print('=' * 20)
    print(cookie_str)
    print('=' * 20)
    print("开始测试Cookie状态")
    # https://api.bilibili.com/x/web-interface/nav
    user = session.get("https://api.bilibili.com/x/web-interface/nav", headers={"cookie": cookie_str}, headers=headers)
    if user.status_code == 412:
        print("被412风控，登录态未知。")
        return cookie_str
    user = user.json()
    if(user["data"]["isLogin"]):
        print("用户 "+user["data"]["uname"]+" 登录成功")
    else:
        print("登录失败")
        exit()
    return cookie_str

if __name__ == "__main__":
    login()