# Copyright (c) 2023-2024 ZianTT, FriendshipEnder
import base64
import json
import time

import qrcode
import requests
from loguru import logger

from utils import prompt

import inquirer

from i18n import i18n
from globals import *

def cookie(cookies):
    lst = []
    for item in cookies.items():
        lst.append(f"{item[0]}={item[1]}")

    cookie_str = ";".join(lst)
    return cookie_str


def appsign(params):
    import hashlib
    import urllib.parse
    appkey = '1d8b6e7d45233436'
    appsec = '560c52ccd288fed045859ed18bffd973'
    params.update({'appkey': appkey})
    params = dict(sorted(params.items()))  # 按照 key 重排参数
    query = urllib.parse.urlencode(params)  # 序列化参数
    sign = hashlib.md5((query + appsec).encode()).hexdigest()  # 计算 api 签名
    params.update({'sign': sign})
    return params


def _verify(gt, challenge, token):
    # global sdk
    from geetest import run
    time_start = time.time()
    data = run(gt, challenge, token, "local_gt")
    delta = time.time() - time_start
    # sdk.metrics.distribution(
    #     key="gt_solve_time",
    #     value=delta * 1000,
    #     unit="millisecond"
    # )
    return data


def qr_login(session, headers):
    global i18n_lang
    from globals import i18n_lang
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
    logger.info(i18n[i18n_lang]["qr_login"])
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
            logger.success(i18n[i18n_lang]["login_success"])
            cookies = requests.utils.dict_from_cookiejar(session.cookies)
            break
        elif check["code"] == 86101:
            pass
        elif check["code"] == 86090:
            logger.info(check["message"])
        elif check["code"] == 86083:
            logger.error(check["message"])
            return qr_login(session, headers)
        elif check["code"] == 86038:
            logger.error(check["message"])
            return qr_login(session, headers)
        else:
            logger.error(check)
            return qr_login(session, headers)
    return cookie(cookies)


def verify_code_login(session, headers):
    global i18n_lang
    from globals import i18n_lang
    # https://passport.bilibili.com/x/passport-login/captcha
    captcha = session.get(
        "https://passport.bilibili.com/x/passport-login/captcha", headers=headers
    ).json()
    gt = captcha["data"]["geetest"]["gt"]
    challenge = captcha["data"]["geetest"]["challenge"]
    token = captcha["data"]["token"]
    tel = prompt([inquirer.Text("tel", message=i18n[i18n_lang]["input_phone_num"], validate=lambda _, x: len(x) == 11)])["tel"]
    logger.info(i18n[i18n_lang]["input_auto_verify"])
    cap_data = _verify(gt, challenge, token)
    while cap_data == False:
        logger.error(i18n[i18n_lang]["input_verify_fail"])
        captcha = session.post(
            "https://passport.bilibili.com/x/passport-login/captcha",
            headers=headers,
        ).json()
        gt = captcha["data"]["geetest"]["gt"]
        challenge = captcha["data"]["geetest"]["challenge"]
        token = captcha["data"]["token"]
        cap_data = _verify(gt, challenge, token)
    logger.success(i18n[i18n_lang]["input_verify_success"])
    data = {
        "cid": "86",
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
        return verify_code_login(session, headers)
    else:
        logger.success(i18n[i18n_lang]["sms_code_send_ok"])
        send_token = send["data"]["captcha_key"]
    while True:
        code = prompt([inquirer.Text("code", message=i18n[i18n_lang]["input_sms_code"], validate=lambda _, x: len(x) == 6)])["code"]
        # https://passport.bilibili.com/x/passport-login/web/login/sms
        data = {"cid": "86", "tel": tel, "captcha_key": send_token, "code": code}
        login = session.post(
            "https://passport.bilibili.com/x/passport-login/web/login/sms",
            headers=headers,
            data=data,
        ).json()
        if login["code"] != 0:
            logger.error(f"{login['code']}: {login['message']}")
        else:
            logger.success(i18n[i18n_lang]["login_success"])
            cookies = requests.utils.dict_from_cookiejar(session.cookies)
            return cookie(cookies)


def verify_code_login_app(session, headers):
    global i18n_lang
    from globals import i18n_lang
    logger.warning(i18n[i18n_lang]["beta_test_func"])
    import uuid
    def buvid():
        import hashlib
        import random
        mac = []
        for i in range(6):
            num = random.randint(0, 0xff)
            mac.append(hex(num)[2:])
        md5 = hashlib.md5(":".join(mac).encode()).hexdigest()
        md5Arr = list(md5)
        return f"XY{md5Arr[2]}{md5Arr[12]}{md5Arr[22]}{md5}"

    # https://passport.bilibili.com/x/passport-login/captcha
    # captcha = session.get(
    #     "https://passport.bilibili.com/x/passport-login/captcha", headers=headers
    # ).json()
    # gt = captcha["data"]["geetest"]["gt"]
    # challenge = captcha["data"]["geetest"]["challenge"]
    # token = captcha["data"]["token"]
    tel = prompt([inquirer.Text("tel", message=i18n[i18n_lang]["input_phone_num"], validate=lambda _, x: len(x) == 11)])["tel"]
    # logger.info(i18n[i18n_lang]["input_auto_verify"])
    # cap_data = _verify(gt, challenge, token)
    # while cap_data == False:
    #     logger.error(i18n[i18n_lang]["input_verify_fail"])
    #     captcha = session.post(
    #         "https://passport.bilibili.com/x/passport-login/captcha",
    #         headers=headers,
    #     ).json()
    #     gt = captcha["data"]["geetest"]["gt"]
    #     challenge = captcha["data"]["geetest"]["challenge"]
    #     token = captcha["data"]["token"]
    #     cap_data = _verify(gt, challenge, token)
    logger.success(i18n[i18n_lang]["input_verify_success"])
    session_id = uuid.uuid4().hex.upper()
    buvid = buvid()
    data = {
        "cid": "86",
        "tel": tel,
        "login_session_id": session_id,
        # "recaptcha_token": token,
        # "gee_challenge": cap_data["challenge"],
        # "gee_validate": cap_data["validate"],
        # "gee_seccode": cap_data["seccode"] + "|jordan",
        "channel": "bili",
        "buvid": buvid,
        "local_id": buvid,
        "statistics": '{"appId":1,"platform":3,"version":"8.0.0","abtest":""}',
        "ts": round(time.time())
    }
    logger.debug(data)
    # https://passport.bilibili.com/x/passport-login/sms/send
    send = session.post(
        "https://passport.bilibili.com/x/passport-login/sms/send",
        headers=headers,
        data=appsign(data),
    ).json()
    if send["code"] != 0:
        logger.error(f"{send['code']}: {send['message']}")
        return verify_code_login_app(session, headers)
    else:
        logger.success(i18n[i18n_lang]["sms_code_send_ok"])
        send_token = send["data"]["captcha_key"]
    while True:
        code = prompt([inquirer.Text("code", message=i18n[i18n_lang]["input_sms_code"], validate=lambda _, x: len(x) == 6)])["code"]
        # https://passport.bilibili.com/x/passport-login/login/sms
        data = {"cid": 86, "tel": int(tel), "captcha_key": send_token, "code": int(code),
                "login_session_id": session_id}
        login = session.post(
            "https://passport.bilibili.com/x/passport-login/login/sms",
            headers=headers,
            data=appsign(data),
        ).json()
        if login["code"] != 0:
            logger.error(f"{login['code']}: {login['message']}")
        else:
            logger.success(i18n[i18n_lang]["login_success"])
            cookies = requests.utils.dict_from_cookiejar(session.cookies)
            return cookie(cookies)


def password_login(session, headers):
    global i18n_lang
    from globals import i18n_lang
    from Crypto.Cipher import PKCS1_v1_5
    from Crypto.PublicKey import RSA

    username = prompt([inquirer.Text("username", message=i18n[i18n_lang]["input_user_name"])])["username"]
    password = prompt([inquirer.Password("password", message=i18n[i18n_lang]["input_user_password"])])["password"]
    captcha = session.get(
        "https://passport.bilibili.com/x/passport-login/captcha", headers=headers
    ).json()
    gt = captcha["data"]["geetest"]["gt"]
    challenge = captcha["data"]["geetest"]["challenge"]
    token = captcha["data"]["token"]
    logger.info(i18n[i18n_lang]["input_auto_verify"])
    cap_data = _verify(gt, challenge, token)
    while cap_data == False:
        captcha = session.get(
            "https://passport.bilibili.com/x/passport-login/captcha",
            headers=headers,
        ).json()
        gt = captcha["data"]["geetest"]["gt"]
        challenge = captcha["data"]["geetest"]["challenge"]
        token = captcha["data"]["token"]
        logger.error(i18n[i18n_lang]["input_verify_fail"])
        cap_data = _verify(gt, challenge, token)
    logger.success(i18n[i18n_lang]["input_verify_success"])
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
            logger.error(i18n[i18n_lang]["request_too_slow"])
        return password_login(session, headers)
    else:
        if login["data"]["status"] == 2 or login["data"]["status"] == 1:
            logger.warning(i18n[i18n_lang]["need_2nd_verify"])
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
                logger.info(i18n[i18n_lang]["phone_banded"])
                tel = info["data"]["account_info"]["hide_tel"]
                logger.info(i18n[i18n_lang]["will_send_sms"] + tel)
            captcha = session.post(
                "https://passport.bilibili.com/x/safecenter/captcha/pre",
                headers=headers,
            ).json()
            gt = captcha["data"]["gee_gt"]
            challenge = captcha["data"]["gee_challenge"]
            token = captcha["data"]["recaptcha_token"]
            logger.info(i18n[i18n_lang]["input_auto_verify"])
            cap_data = _verify(gt, challenge, token)
            while cap_data == False:
                logger.error(i18n[i18n_lang]["input_verify_fail"])
                captcha = session.post(
                    "https://passport.bilibili.com/x/safecenter/captcha/pre",
                    headers=headers,
                ).json()
                gt = captcha["data"]["gee_gt"]
                challenge = captcha["data"]["gee_challenge"]
                token = captcha["data"]["recaptcha_token"]
                cap_data = _verify(gt, challenge, token)
            logger.success(i18n[i18n_lang]["input_verify_success"])
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
                return password_login(session, headers)
            else:
                logger.success(i18n[i18n_lang]["sms_code_send_ok"])
                send_token = send["data"]["captcha_key"]
            while True:
                code = prompt([inquirer.Text("code", message=i18n[i18n_lang]["input_sms_code"], validate=lambda _, x: len(x) == 6)])[
                    "code"]
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
                    logger.success(i18n[i18n_lang]["login_success"])
                    code = send["data"]["code"]
                    data = {"source": "risk", "code": code}
                    session.post(
                        "https://passport.bilibili.com/x/passport-login/web/exchange_cookie",
                        headers=headers,
                        data=data,
                    ).json()
                    cookies = requests.utils.dict_from_cookiejar(session.cookies)
                    return cookie(cookies)
        logger.success(i18n[i18n_lang]["login_success"])
        cookies = requests.utils.dict_from_cookiejar(session.cookies)
        return cookie(cookies)


def sns_login(session, headers):
    global i18n_lang
    from globals import i18n_lang
    method = \
    prompt([inquirer.List("method", message=i18n[i18n_lang]["choose_sns_login"],\
        choices=[i18n[i18n_lang]["sns_micromessage"],\
                 i18n[i18n_lang]["sns_qq"],\
                 i18n[i18n_lang]["sns_microblog"]],\
         default=i18n[i18n_lang]["sns_micromessage"])])["method"]
    if method == i18n[i18n_lang]["sns_micromessage"]:
        sns = "wechat"
    elif method == i18n[i18n_lang]["sns_qq"]:
        sns = "qq"
    elif method == i18n[i18n_lang]["sns_microblog"]:
        sns = "weibo"
    else:
        logger.error(i18n[i18n_lang]["login_not_supported"])
        return sns_login(session, headers)
    # https://passport.bilibili.com/x/passport-login/web/sns/state/generate
    state = session.get(
        "https://passport.bilibili.com/x/passport-login/web/sns/state/generate",
        headers=headers,
    ).json()["data"]["csrf_state"]
    # https://passport.bilibili.com/x/passport-login/web/sns/authorize/url
    data = {
        "sns_platform": sns,
        "csrf_state": state,
        "gourl": "http://127.0.0.1/",
        "source": "main-fe-header",
    }
    url = session.post(
        "https://passport.bilibili.com/x/passport-login/web/sns/authorize/url",
        headers=headers,
        data=data,
    ).json()["data"]["url"]
    logger.info(url)
    logger.info(i18n[i18n_lang]["open_in_browser"])
    # https://passport.bilibili.com/x/passport-login/web/sns/login
    redirect = prompt([inquirer.Text("redirect", message=i18n[i18n_lang]["input_redirect"])])["redirect"]
    # get params from redirect
    try:
        redirect = redirect.split("?")[1]
        params = {}
        for item in redirect.split("&"):
            key, value = item.split("=")
            params[key] = value
        data = {
            "csrf_state": state,
            "gourl": params["go_url"],
            "source": "main-fe-header",
            "sns_platform": params["sns_platform"],
            "code": params["code"],
        }
    except Exception:
        logger.error(i18n[i18n_lang]["connect_link_error"])
        return sns_login(session, headers)
    login = session.post(
        "https://passport.bilibili.com/x/passport-login/web/sns/login",
        headers=headers,
        data=data,
    ).json()
    if login["code"] != 0:
        logger.error(f"{login['code']}: {login['message']}")
    else:
        if not login["data"]["has_bind"]:
            logger.error(i18n[i18n_lang]["connect_no_account"])
            return sns_login(session, headers)
        logger.success(i18n[i18n_lang]["login_success"])
        cookies = requests.utils.dict_from_cookiejar(session.cookies)
        return cookie(cookies)


def interactive_login(sentry_sdk=None):
    global i18n_lang
    from globals import i18n_lang
    # global sdk
    # sdk = sentry_sdk
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0"
    }

    session = requests.session()
    session.get("https://www.bilibili.com/", headers=headers)

    try: # 登录方式 cookie 扫码 用户名密码 web短信 app短信 sns
        method = prompt([inquirer.List("method", message=i18n[i18n_lang]["bi_login_method"],
                                       choices=[i18n[i18n_lang]["bi_login_cookie"], i18n[i18n_lang]["bi_login_qrcode"], \
                                                i18n[i18n_lang]["bi_login_user_pass"], i18n[i18n_lang]["bi_login_web_sms"], \
                                                i18n[i18n_lang]["bi_login_app_sms"], i18n[i18n_lang]["bi_login_sns"]],
                                       default= i18n[i18n_lang]["bi_login_qrcode"])]) #默认扫码
        if method["method"] == i18n[i18n_lang]["bi_login_cookie"]:
            cookie_str = input(i18n[i18n_lang]["bi_input_cookie"])
            # verify cookie
            try:
                session.get("https://www.bilibili.com/",
                            headers={"User-Agent": "Mozilla/5.0 BiliApp/80000100", "Cookie": cookie_str})
            except Exception:
                logger.error(i18n[i18n_lang]["bi_illegal_cookie"])
                return interactive_login()
        elif method["method"] == i18n[i18n_lang]["bi_login_qrcode"]:
            cookie_str = qr_login(session, headers)
        elif method["method"] == i18n[i18n_lang]["bi_login_user_pass"]:
            cookie_str = password_login(session, headers)
        elif method["method"] == i18n[i18n_lang]["bi_login_web_sms"]:
            cookie_str = verify_code_login(session, headers)
        elif method["method"] == i18n[i18n_lang]["bi_login_sns"]:
            cookie_str = sns_login(session, headers)
        elif method["method"] == i18n[i18n_lang]["bi_login_app_sms"]:
            cookie_str = verify_code_login_app(session, headers)
        else:
            logger.error(i18n[i18n_lang]["login_not_supported"])
            return interactive_login()
    except Exception as e:
        logger.error(i18n[i18n_lang]["login_failed"])
        return interactive_login()

    logger.debug("=" * 20)
    logger.debug(cookie_str)
    logger.debug("=" * 20)
    return cookie_str
