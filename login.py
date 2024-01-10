import time
import requests
import requests.utils
import qrcode
import os

def exit():
    os._exit(0)

def login():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BHYG/1.5.2"
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
    # add cookie header to headers
    headers.update({"cookie": cookie_str})
    user = session.get("https://api.bilibili.com/x/web-interface/nav", headers=headers)
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