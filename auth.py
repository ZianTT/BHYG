# -*- coding: UTF-8 -*-
# provide utils for this app's user authentication

import base64
import hashlib
import json
import os
import platform
import sys
import time
import jwt

import requests
from loguru import logger

from globals import *


def get_github_token(session):
    global github_token
    if os.path.exists("gh_token"):
        with open("gh_token", "r") as f:
            github_token = f.read()
        return github_token
    mirror = input("是否使用镜像站点？(Y/n)")
    if mirror.lower() == "n":
        url_base = "https://github.com"
    else:
        url_base = "https://kkgithub.com"
    try:
        code = session.post(
            url_base + "/login/device/code",
            data={"client_id": "0ea323be20ab6b75e944"},
            headers={"Accept": "application/json"},
        ).json()
    except requests.exceptions.ConnectionError:
        logger.error("无法连接到GitHub，建议尝试镜像站点")
        return get_github_token(session)
    device_code = code["device_code"]
    user_code = code["user_code"]
    verification_uri = code["verification_uri"]
    logger.info(f"请打开 {verification_uri} 并输入 {user_code} 进行验证")
    os.system(f"start {verification_uri}")
    pending = True
    while pending:
        time.sleep(5)
        token = session.post(
            url_base + "/login/oauth/access_token",
            data={
                "client_id": "0ea323be20ab6b75e944",
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        ).json()
        if "error" in token:
            if token["error"] == "authorization_pending":
                continue
            else:
                logger.error(token["error_description"])
                return
        else:
            pending = False
    gh_token = token["access_token"]
    with open("gh_token", "w") as f:
        f.write(gh_token)
    return gh_token


def get_machine_code():

    # NOTE: Adopt macos

    def _macos():
        try:
            import subprocess

            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise Exception("Failed to get hardware information")
            serial_number = ""
            for line in result.stdout.splitlines():
                if "Serial Number" in line:
                    serial_number = line.split(":")[1].strip()
                    break
            if serial_number == "":
                raise Exception("Serial number not found")
            combine_str = serial_number + "bhyg-salt"
            return combine_str
        except Exception as e:
            logger.error(f"An error occurred in _macos: {e}")
            return None

    def _win():
        try:
            import wmi

            m_wmi = wmi.WMI()
            cpu_info = m_wmi.Win32_Processor()
            if len(cpu_info) > 0:
                cpu_serial = cpu_info[0].ProcessorId
                if cpu_serial is None:
                    cpu_serial = ""
            else:
                cpu_serial = ""

            board_info = m_wmi.Win32_BaseBoard()
            if len(board_info) > 0:
                board_serial = board_info[0].SerialNumber.strip().strip(".")
                if board_serial is None:
                    board_serial = ""
            else:
                board_serial = ""

            combine_str = cpu_serial + board_serial + "bhyg-salt"
            return combine_str
        except Exception as e:
            logger.error(f"An error occurred in _win: {e}")
            return None

    if platform.system() == "Windows":
        combine_str = _win()
    elif platform.system() == "Darwin":
        combine_str = _macos()
    else:
        logger.error("Platform not yet supported.")
        sys.exit()

    combine_byte = combine_str.encode("utf-8")
    machine_code = hashlib.md5(combine_byte).hexdigest()
    return machine_code


# def verify(key):
#     global uid
#     global bhyg_username
#     try:
#         rsa_priv = """-----BEGIN RSA PRIVATE KEY-----
#     MIIEogIBAAKCAQEAkazjBRGNcYV/RfTjOgach54ueXHZlDHWqVyLxuVjfeOYbzNt
#     k+tmd0nZweBCmFnrVM/MSAfU3fjI2XuFRP00Jjnevct0f3uj4BmkCH1RehjQgPlg
#     Xrspb+cEbulMPFlxLrOB61TvInDEn0lbyiN4ini7ALEzKj36usTCR8yTy3IrVHFe
#     6Z1zggCuu/up/hGZEDxtNXtyLDEnMrutq7sEQvFIhfSQ4ng6Vgf0SJetOKEazdie
#     SBPGRqihfT8Mppng1o3AOQkegqqo6vRYmAMwuBZWi0xUteX8KnjzSqr6O8z1X+iq
#     FZ6RJpWLbyDlHkqo6Jd4rzl1OR02E7b9X5S/hQIDAQABAoIBAAOJVe2Okod5/S/+
#     lPGYrX4hWfF60RRm7VYpN/95HCQ3PUEd14Aqy88DjPTG8/bs3+isLsJk5kcJPh8B
#     f6fAGd7/sqea49Ygc0cCeFf4atzy80TeSPejxYrA6fujUEV6ymOe2f2Tj0afxDY1
#     urO6jreV3LxUkPBqlsan9it2DPR4ZLA7JSacauqkag0gq5m0+IQO/8brmiT2A5m6
#     tOKF++8lpniHYuehI7Pv10Fhv3FmOngeuA5yIMOc5Id7I3jM/lgDlzG2kUlpJAp0
#     cxYEUW9iI0Se38d0SVHjm6VUb8IA9C/PGbxKN7V70Jw+NLl9U/gYnFmpTveXdO2t
#     PbuPWdUCgYEAuM4gzcMJkRAz13HmJGCGR+gDVih9kS8unaudwGeP5MIKkpzKhNJe
#     Z+osntGMpQPopUmEhePkwGJZrNFgShEJNDu84jk9/5ATde76JxXH0296InEqGTiX
#     TCNgglWJ5hrCE5Vlr1NZ8yQuN3CkgnhCb7Au+Nj6kfg5y0KO/91U/a8CgYEAycux
#     DHF3zVs4X/i1/PI/0RJq/z/wB9Y0z2bi783DbTMXCylja6NSaDYwGZKOrjx/Mq9r
#     uE3y+L1DgjUs97FTqv6WbNWDhKSkza3cBGFXnGgOLi/+cndX5UJR9Y2na5cxd/Qj
#     zAiXUpfM2BZ9hFOj5+UggMIv+7okgAj2hsr29wsCgYArGrkABTvYAAV3fPOHDJSF
#     dRJCKFORZ4Xh9MNouz8OxkudAsEh1cd7SV169bluS8kZtFoauJsEXGw6KOPiorKY
#     4k4eHefeEgbX/ROPxj7DjD7ahbaiB1cSxTWfcMAnUZpu4uvCxxg14/x7peRZIh+s
#     2VU7abCYF2OziyS7fS5ztQKBgEoZSrT4AXbd1TCggisUxUw/SBzcXIZ0KMYz0Icf
#     9m/lv8NwejpvKXZs13K8dzoRqt9wvMxbiym9TcnFPvLhIYj7nT7vlDCjyIRiIBVX
#     rTUYnIRnSTa9DgB4PuI9FsoSJa8XbgGg8ff5F9YNRB/QGrKvVyUQqU/1BSwinmvW
#     oaMLAoGAJx726lHlcJASjwsLIE3EW+ijV8iQx0r/ArjeDvRHJgSBWb9jlvyEYZGR
#     9QaYcxiykhiYt9Ktd3xaqeU5v28dHeWeFtpCgE6/ImthMI+E48/SQBQmdhOYmyLR
#     9RDkLEYVnTl6fjl5DKEXUcwEWuKD+J+qzud8kw2BRu9csB9hm/Q=
#     -----END RSA PRIVATE KEY-----"""
#         cipher = PKCS1_v1_5.new(RSA.importKey(rsa_priv))
#         data = json.loads(cipher.decrypt(base64.b64decode(key), 0).decode("utf-8"))

#         # NOTE: debug print
#         logger.debug(f"verification data: {data}")

#         logger.info(
#             f"欢迎用户{data['user']}! 距离授权过期还有{
#                     int((data['expire']-time.time())/86400)}天"
#         )
#         bhyg_username = data["user"]
#         sentry_sdk.set_user({"username": data["user"]})
#         if "uid" in data:
#             uid = data["uid"]
#         else:
#             uid = None
#         if data["machine_code"] != get_machine_code():
#             logger.error("机器码不正确")
#             logger.warning(
#                 "PS: 机器码在0.6.1版本更换了新算法，请联系分发人提供新的激活码或授权码"
#             )
#             return False
#         if time.time() > data["expire"]:
#             logger.error("授权已过期")
#             return False
#         return True
#     except:
#         logger.error("授权错误")
#         return False


# NOTE: Changed implementation.
# PrivKey should NEVER be hard coded into program, use pubkey signature for verification instead
def verify(combined_key):
    global uid
    global bhyg_username

    if not combined_key or combined_key == "":
        logger.debug("Key is empty.")
        return None

    try:
        public_key = """-----BEGIN PUBLIC KEY-----
MIGbMBAGByqGSM49AgEGBSuBBAAjA4GGAAQBgc4HZz+/fBbC7lmEww0AO3NK9wVZ
PDZ0VEnsaUFLEYpTzb90nITtJUcPUbvOsdZIZ1Q8fnbquAYgxXL5UgHMoywAib47
6MkyyYgPk0BXZq3mq4zImTRNuaU9slj9TVJ3ScT3L1bXwVuPJDzpr5GOFpaj+WwM
Al8G7CqwoJOsW7Kddns=
-----END PUBLIC KEY-----"""

        

        # Verify the signature
        try:
            data = jwt.decode(combined_key, public_key, algorithms=['ES512'])
            logger.info(
                f"欢迎用户{data['user']}! 距离授权过期还有{int((data['exp'] - time.time()) / 86400)}天。欢迎使用全新0.7.0版本"
            )
            bhyg_username = data["user"]
            sentry_sdk.set_user({"username": data["user"]})

            if data["machine_code"] != get_machine_code():
                logger.error("机器码不正确")
                return False

            return data
        except jwt.exceptions.ExpiredSignatureError:
            logger.error("授权已过期")
            return None
        except (jwt.exceptions.InvalidSignatureError, jwt.exceptions.DecodeError):
            logger.error("签名验证失败")
            return None
    except Exception as e:
        logger.error(f"授权错误: {e}")
        return None


def interactive_registration(session):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BHYG/0.7.0",
        "Referer": "https://www.bilibili.com/",
    }
    session.get("https://space.bilibili.com/1", headers=headers)
    logger.info(
        "欢迎使用！软件官方链接 https://github.com/ZianTT/BHYG 任何非官方链接下载或由ZianTT(zeroplex)授权的下载都是盗版（如PYC运行版）"
    )
    logger.info(
        "本程序提供个人版激活码，若您确认为个人使用您可以在点击GitHub项目Star后输入您的GitHub用户名(而非姓名)获取一个免费的7天许可证，到期可再次获取。"
    )
    logger.info(
        "若您拥有激活码或需人工激活，请输入n"
    )
    individual = input("是否为个人使用？(Y/n)")
    if individual.lower() == "n":
        key = input("本机机器码：" + get_machine_code() + "请输入授权码或激活码：")
        if len(key) == 8:
            uid = None
            logger.info(
                "激活需要绑定您的Bilibili UID，请输入您的UID(若您的激活码为多人版，请输入任意数字)"
            )
            while True:
                try:
                    uid = int(input("UID:"))
                except ValueError:
                    logger.error("UID必须为数字")
                    continue
                confirm = input("请确认是否为您的账号，一经绑定，无法修改(y/N):")
                if confirm.lower() != "y":
                    logger.error("绑定失败")
                else:
                    break
            try:
                key = session.get(
                    f"https://bhyg.bitf1a5h.eu.org/v0.7/activate?code={key}&mc={get_machine_code()}&uid={uid}"
                ).json()
            except Exception:
                logger.error("激活失败")
                logger.error("服务器故障或网络连接错误")
                logger.error("请尝试手动激活")
                return
            if key == None:
                logger.error("激活码无效")
                logger.info("即将退出")
                time.sleep(10)
                return
        with open("key", "w", encoding="utf-8") as f:
            f.write(key)
    else:
        while True:
            uid = None
            logger.info("请确认您已点击项目主页的Star")
            gh_token = get_github_token(session)
            logger.info(
                "激活需要绑定您的Bilibili UID，请输入您的UID(若您的激活码为多人版，请输入任意数字)"
            )
            try:
                uid = int(input("UID:"))
            except ValueError:
                logger.error("UID必须为数字")
                continue
            confirm = input("请确认是否为您的账号，一经绑定，无法修改(y/N):")
            if confirm.lower() != "y":
                logger.error("绑定失败")
                continue
            try:
                data = requests.get(
                    f"https://bhyg.bitf1a5h.eu.org/v0.7/individual?gh_token={gh_token}&mc={get_machine_code()}&uid={uid}"
                ).json()
            except Exception:
                logger.error("激活失败")
                logger.error("服务器故障或网络连接错误")
                logger.error("请尝试手动激活")
                continue
            if data["success"]:
                key = data["key"]
                with open("key", "w", encoding="utf-8") as f:
                    f.write(key)
                break
            else:
                logger.error("激活失败")
                logger.error(data["msg"])
                continue
