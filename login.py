import time
import requests
import requests.utils
import pyqrcode

def getCookies(cookie_jar, domain):
    cookie_dict = cookie_jar.get_dict(domain=domain)
    found = ['%s=%s' % (name, value) for (name, value) in cookie_dict.items()]
    return ';'.join(found)


generate = requests.get("https://passport.bilibili.com/x/passport-login/web/qrcode/generate")
generate = generate.json()
if generate['code'] == 0:
    url = generate['data']['url']
else:
    print(generate)
    exit()
qr = pyqrcode.create(url)
print(qr.terminal(quiet_zone=2, background="white"))
print("请使用Bilibili手机客户端扫描二维码")
while True:
    req = requests.get("https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key="+generate['data']['qrcode_key'])
    check = req.json()["data"]
    if check['code'] == 0:
        print("登录成功")
        url = check["url"]
        cookies = getCookies(req.cookies, ".bilibili.com")
        break
    elif check['code'] == 86101:
        pass
    elif check['code'] == 86090:
        print(check["message"])
    else:
        print(check)
        exit()
    time.sleep(1)
print("Cookies:"+cookies)
pause = input("按回车将继续生成cookie配置文件到当前目录...")
config_string = "cookie="+cookies
with open("config.txt", "w", encoding="utf-8") as f:
    f.write(config_string)
print("配置文件已生成，程序将在5s内退出")
time.sleep(5)