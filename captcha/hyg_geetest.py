# -*- coding: utf-8 -*-
import threading,execjs, requests, time, json
from urllib import request
from captcha.gap import *
from captcha.trace import *

class VerifyFail(Exception):
    pass

def main(cookie, voucher):
    csrf = cookie[cookie.index("bili_jct") + 9:cookie.index("bili_jct") + 41]    
    url = "https://show.bilibili.com/openplatform/verify/tool/geetest/prepare?oaccesskey="
    data = {
        "verify_type": 1,
        "business": "shield",
        "voucher": voucher,
        "client_type": "h5",
        "csrf": csrf
    }
    headers = {
        "cookie": cookie,
        "referer": "https://mall.bilibili.com/activities/verify/index.html",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; Redmi K30 5G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Mobile Safari/537.36"
    }
    res = requests.post(url, data=data, headers=headers ).json()['data']
    gt = res['captcha_id']
    challenge = res['challenge']
    geetest_voucher = res['geetest_voucher']
    res = requests.get("https://api.geetest.com/ajax.php?gt=" + gt + "&challenge=" + challenge + "&lang=zh-cn&pt=0&w=&callback=geetest_1690369845920").text
    url = "https://api.geetest.com/get.php?is_next=true&type=slide3&gt=" + gt + "&challenge=" + challenge + "&lang=zh-cn&https=true&protocol=https%3A%2F%2F&offline=false&product=embed&api_server=api.geetest.com&isPC=true&autoReset=true&width=100%25&callback=geetest_1690369845920"
    res = requests.get(url).text
    res = json.loads(res[res.index("(") + 1:res.rindex(")")])
    challenge = res['challenge']
    s = res['s']
    request.urlretrieve('https://static.geetest.com/' + res['fullbg'], 'img/oldallbg.png')
    request.urlretrieve('https://static.geetest.com/' + res['bg'], 'img/oldbg.png')
    request.urlretrieve('https://static.geetest.com/' + res['slice'], 'img/slide.png')
    restore_picture()
    distance = get_gap()
    track = get_track(distance - 5)
    with open('jiyan.js', 'r', encoding='utf-8') as f:
        js = execjs.compile(f.read())
    passtime = track[-1][-1]
    track = js.call('get_encode_trace', track, s)
    w = js.call('get_w', distance - 5, track, challenge, challenge[:32], passtime, str(random.randint(100, 200)),gt)
    url = "https://api.geetest.com/ajax.php?gt=" + gt + "&challenge=" + challenge + "&lang=zh-cn&pt=0&w=" + w + "&callback=geetest_1690369845920"
    res = requests.get(url).text
    res = json.loads(res[res.index("(") + 1:res.rindex(")")])
    validate = res['validate']
    url = "https://show.bilibili.com/openplatform/verify/tool/geetest/check?oaccesskey="
    data = {
        "success": 1,
        "captcha_id": gt,
        "challenge": challenge,
        "validate": validate,
        "seccode": validate + "|jordan",
        "geetest_voucher": geetest_voucher,
        "client_type": "h5",
        "csrf": csrf
    }
    headers = {
        "cookie": cookie,
        "referer": "https://mall.bilibili.com/activities/verify/index.html",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; Redmi K30 5G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Mobile Safari/537.36"
    }
    res = requests.post(url, data=data, headers=headers).json()["code"]
    if res == 0:
        print("验证成功")
    else:
        print("验证失败")
        raise VerifyFail

def verify(cookie, voucher):
    try:
        for i in range(1):
            thr = threading.Thread(target=main, args=(cookie, voucher))
            thr.start()
            time.sleep(2)
        return True
    except VerifyFail:
        return False

if __name__ == '__main__':
    cookie = "SESSDATA=e3c2c829%2C1705922881%2Cf22e6%2A72u2vKevPSZDaZQ7FNKW4orGDhMm2C4MwnDTfsWerdNiAbkAafmdAPCokaYHzgx6jvTEvXQAAALAA;bili_jct=36c372716a1d2b254d6a6f6af7094ea6;DedeUserID=531718444;DedeUserID__ckMd5=84919e1b081d6646;sid=o6sh50kq"
    voucher = "qkWbP+iwp7BCK7xVre32eTQM4f3CINkMVzSTMCSPXiehFySnVDX87gA/swTmYaVzZ7yRYIcyNHeNE6GYcud56zlnsGpiN/dPUD3qddJPgR1TlrEZaKVh4pbAkdkTNLUb1zePmbe6kt4YtGPATb30mJOZXEh9SWmtwAk7gCv1u3gPXtVGz0tz/BUEkJpzwxtoer1fMXRnSg500AHL4Dji0ile5EhKXTAYtBYLpBj3acE="
    verify(cookie, voucher)
