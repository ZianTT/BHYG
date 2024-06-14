import base64
import json
import time

import qrcode
import requests
from loguru import logger


def cookie(cookies):
    lst = []
    for item in cookies.items():
        lst.append(f"{item[0]}={item[1]}")

    cookie_str = ";".join(lst)
    return cookie_str



def _verify(gt, challenge, token):
    from geetest import run
    from threading import Thread
    th = Thread(target = run, args =(gt, challenge, token, ),daemon=True)
    th.start()
    pending_captcha = {"gt": gt, "challenge": challenge, "token": token}
    with open("data/toc", "w") as f:
        f.write(json.dumps({"type": "geetest", "data": pending_captcha}))
    with open("data/tos", "a+") as f:
        while True:
            f.seek(0, 0)
            data = f.read()
            if data != "":
                captcha_data = json.loads(data)
                if captcha_data["success"] == False:
                    f.truncate(0)
                    return False
                f.truncate(0)
                return captcha_data


def qr_login(session, headers):
    generate = session.get(
        "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
        headers=headers,
    )
    generate = generate.json()
    if generate["code"] == 0:
        url = generate["data"]["url"]
    else:
        logger.error(generate)
        return
    qr = qrcode.QRCode()
    qr.add_data(url)
    qr.print_ascii(invert=True)
    img = qr.make_image()
    img.show()
    logger.info("请使用Bilibili手机客户端扫描二维码")
    while True:
        time.sleep(1)
        url = (
            "https://passport.bilibili.com/x/passport-login/web/qrcode/poll?source=main-fe-header&qrcode_key="
            + generate["data"]["qrcode_key"]
        )
        req = session.get(url, headers=headers)
        # read as utf-8
        check = req.json()["data"]
        if check["code"] == 0:
            logger.success("登录成功")
            cookies = requests.utils.dict_from_cookiejar(session.cookies)
            break
        elif check["code"] == 86101:
            pass
        elif check["code"] == 86090:
            logger.info(check["message"])
        elif check["code"] == 86083:
            logger.error(check["message"])
            return qr_login(session)
        elif check["code"] == 86038:
            logger.error(check["message"])
            return qr_login(session)
        else:
            logger.error(check)
            return qr_login(session)
    return cookie(cookies)


def verify_code_login(session, headers):
    # https://passport.bilibili.com/x/passport-login/captcha
    captcha = session.get(
        "https://passport.bilibili.com/x/passport-login/captcha", headers=headers
    ).json()
    gt = captcha["data"]["geetest"]["gt"]
    challenge = captcha["data"]["geetest"]["challenge"]
    token = captcha["data"]["token"]
    tel = input("请输入手机号（非大陆手机号请添加国家号，如+1 4438888888）: ").split(
        " "
    )
    if len(tel) == 1:
        cid = "+86"
        tel = tel[0]
    else:
        cid = tel[0]
        tel = tel[1]
    logger.info("请完成验证")
    cap_data = _verify(gt, challenge, token)
    while cap_data == False:
        logger.error("验证失败，请重新验证")
        captcha = session.post(
            "https://passport.bilibili.com/x/passport-login/captcha",
            headers=headers,
        ).json()
        gt = captcha["data"]["geetest"]["gt"]
        challenge = captcha["data"]["geetest"]["challenge"]
        token = captcha["data"]["token"]
        cap_data = _verify(gt, challenge, token)
    logger.success("验证完成")
    data = {
        "cid": cid,
        "tel": tel,
        "token": token,
        "challenge": cap_data["challenge"],
        "validate": cap_data["validate"],
        "seccode": cap_data["seccode"] + "|jordan",
    }
    # https://passport.bilibili.com/x/passport-login/web/sms/send
    send = session.post(
        "https://passport.bilibili.com/x/passport-login/web/sms/send",
        headers=headers,
        data=data,
    ).json()
    if send["code"] != 0:
        logger.error(f"{send['code']}: {send['message']}")
        return verify_code_login(session)
    else:
        logger.success("验证码发送成功")
        send_token = send["data"]["captcha_key"]
    while True:
        code = input("请输入验证码: ")
        # https://passport.bilibili.com/x/passport-login/web/login/sms
        data = {"cid": cid, "tel": tel, "captcha_key": send_token, "code": code}
        login = session.post(
            "https://passport.bilibili.com/x/passport-login/web/login/sms",
            headers=headers,
            data=data,
        ).json()
        if login["code"] != 0:
            logger.error(f"{login['code']}: {login['message']}")
        else:
            logger.success("登录成功")
            cookies = requests.utils.dict_from_cookiejar(session.cookies)
            return cookie(cookies)


def password_login(session, headers):
    from Crypto.Cipher import PKCS1_v1_5
    from Crypto.PublicKey import RSA

    # https://passport.bilibili.com/x/passport-login/web/key
    username = input("请输入用户名（通常为手机号）: ")
    import getpass

    password = getpass.getpass("请输入密码：")
    captcha = session.get(
        "https://passport.bilibili.com/x/passport-login/captcha", headers=headers
    ).json()
    gt = captcha["data"]["geetest"]["gt"]
    challenge = captcha["data"]["geetest"]["challenge"]
    token = captcha["data"]["token"]
    logger.info("请完成验证")
    cap_data = _verify(gt, challenge, token)
    while cap_data == False:
        captcha = session.get(
            "https://passport.bilibili.com/x/passport-login/captcha",
            headers=headers,
        ).json()
        gt = captcha["data"]["geetest"]["gt"]
        challenge = captcha["data"]["geetest"]["challenge"]
        token = captcha["data"]["token"]
        logger.error("验证失败，请重新验证")
        cap_data = _verify(gt, challenge, token)
    logger.success("验证完成")
    key = session.get(
        "https://passport.bilibili.com/x/passport-login/web/key", headers=headers
    ).json()["data"]
    rsa_pub = RSA.importKey(key["key"])
    cipher = PKCS1_v1_5.new(rsa_pub)
    enc = base64.b64encode(cipher.encrypt((key["hash"] + password).encode())).decode(
        "utf8"
    )
    data = {
        "username": username,
        "password": enc,
        "token": token,
        "challenge": cap_data["challenge"],
        "validate": cap_data["validate"],
        "seccode": cap_data["seccode"] + "|jordan",
    }
    login = session.post(
        "https://passport.bilibili.com/x/passport-login/web/login",
        headers=headers,
        data=data,
    ).json()
    if login["code"] != 0:
        logger.error(f"{login['code']}: {login['message']}")
        if login["code"] == -662:
            logger.error("PS: 请求超时，请快一点")
        return password_login(session)
    else:
        if login["data"]["status"] == 2 or login["data"]["status"] == 1:
            logger.warning("需要二次验证")
            # extract tmp_code request_id from login["data"]["url"]
            tmp_token = login["data"]["url"].split("tmp_token=")[1][:32]
            try:
                scene = (
                    login["data"]["url"]
                    .split("tmp_token=")[0]
                    .split("scene=")[1]
                    .split("&")[0]
                )
            except IndexError:
                scene = "loginTelCheck"
            info = session.get(
                "https://passport.bilibili.com/x/safecenter/user/info?tmp_code="
                + tmp_token,
                headers=headers,
            ).json()
            if info["data"]["account_info"]["bind_tel"]:
                logger.info("已绑定手机号")
                tel = info["data"]["account_info"]["hide_tel"]
                logger.info("即将给该手机号发送验证码: " + tel)
            captcha = session.post(
                "https://passport.bilibili.com/x/safecenter/captcha/pre",
                headers=headers,
            ).json()
            gt = captcha["data"]["gee_gt"]
            challenge = captcha["data"]["gee_challenge"]
            token = captcha["data"]["recaptcha_token"]
            logger.info("请完成验证")
            cap_data = _verify(gt, challenge, token)
            while cap_data == False:
                logger.error("验证失败，请重新验证")
                captcha = session.post(
                    "https://passport.bilibili.com/x/safecenter/captcha/pre",
                    headers=headers,
                ).json()
                gt = captcha["data"]["gee_gt"]
                challenge = captcha["data"]["gee_challenge"]
                token = captcha["data"]["recaptcha_token"]
                cap_data = _verify(gt, challenge, token)
            logger.success("验证完成")
            data = {
                "recaptcha_token": token,
                "gee_challenge": cap_data["challenge"],
                "gee_validate": cap_data["validate"],
                "gee_seccode": cap_data["seccode"] + "|jordan",
                "sms_type": scene,
                "tmp_code": tmp_token,
            }
            # https://passport.bilibili.com/x/safecenter/common/sms/send
            send = session.post(
                "https://passport.bilibili.com/x/safecenter/common/sms/send",
                headers=headers,
                data=data,
            ).json()
            if send["code"] != 0:
                logger.error(f"{send['code']}: {send['message']}")
                return password_login(session)
            else:
                logger.success("验证码发送成功")
                send_token = send["data"]["captcha_key"]
            while True:
                code = input("请输入验证码: ")
                data = {
                    "type": "loginTelCheck",
                    "tmp_code": tmp_token,
                    "captcha_key": send_token,
                    "code": code,
                }
                url = "https://passport.bilibili.com/x/safecenter/login/tel/verify"
                if login["data"]["status"] == 1:
                    del data["type"]
                    data["verify_type"] = "sms"
                    url = "https://passport.bilibili.com/x/safecenter/sec/verify"
                send = session.post(url, headers=headers, data=data).json()
                if send["code"] != 0:
                    logger.error(f"{send['code']}: {send['message']}")
                else:
                    logger.success("登录成功")
                    code = send["data"]["code"]
                    data = {"source": "risk", "code": code}
                    session.post(
                        "https://passport.bilibili.com/x/passport-login/web/exchange_cookie",
                        headers=headers,
                        data=data,
                    ).json()
                    cookies = requests.utils.dict_from_cookiejar(session.cookies)
                    return cookie(cookies)
        logger.success("登录成功")
        cookies = requests.utils.dict_from_cookiejar(session.cookies)
        return cookie(cookies)


def interactive_login():

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BHYG/0.7.0"
    }

    session = requests.session()
    session.get("https://www.bilibili.com/", headers=headers)

    logger.info(
        "请选择登录方式\n1. cookie登录\n2. 扫码登录\n3. 用户名密码登录\n4. 验证码登录"
    )
    method = input("请输入数字: ")
    if method == "1":
        cookie_str = input("请输入cookie: ")
    elif method == "2":
        cookie_str = qr_login(session, headers)
    elif method == "3":
        cookie_str = password_login(session, headers)
    elif method == "4":
        cookie_str = verify_code_login(session, headers)
    else:
        logger.error("暂不支持此方式")
        interactive_login()

    logger.debug("=" * 20)
    logger.debug(cookie_str)
    logger.debug("=" * 20)
    return cookie_str
