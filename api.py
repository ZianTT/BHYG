import base64
import json
from math import e
import os
import random
import sys
import time
import httpx

import threading
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import hashlib
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
import questionary
from sentry_sdk.scrubber import EventScrubber
from sentry_sdk.integrations.loguru import LoguruIntegration, LoggingLevels
import sentry_sdk

from bilibili_util import BilibiliClient
from loguru import logger
import security
from push import do_push
from typing import final

POLICY_BASE = "https://not.available.in.oss.invalid"
VERSION = "v1.11.2 OSS"

USE_CAPTCHA = False


class ProtectedMeta(type):
    def __setattr__(cls, name, value):
        if name.startswith("__"):
            raise AttributeError(f"Cannot override {name} in class {cls.__name__}")
        if name in cls.__dict__ and callable(cls.__dict__[name]):
            raise AttributeError(f"Cannot override {name} in class {cls.__name__}")
        super().__setattr__(name, value)


@final
class BHYG(metaclass=ProtectedMeta):
    def __new__(cls, *args, **kwargs):
        if cls is not BHYG:
            raise TypeError(f"Hacker!!!")
        return super().__new__(cls)

    def __init_subclass__(cls, **kwargs):
        raise TypeError(f"Hacker!!!")

    def __init__(
        self
    ):
        global POLICY_BASE, VERSION
        if sys.argv[0].endswith(".py"):
            self.DEBUG = True
        else:
            self.DEBUG = False
        print(f"Version: {VERSION} OSS Ethan")
        self.phrases = {}
        if sys.platform == "win32":
            self.platform = "windows"
        elif sys.platform == "darwin":
            self.platform = "macos"
        elif sys.platform == "linux":
            self.platform = "linux"
        else:
            self.platform = "unknown"
        self.machine_id = security.get_machine_id()
        self.username = None
        self.order_base = "https://show.bilibili.com"
        logger.remove()
        if not self.DEBUG:
            logger.add(
                sys.stdout,
                level="INFO",
                format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <cyan>"
                + self.machine_id[:7]
                + "</cyan> | <level>{level: <8}</level> | <level>{message}</level>",
            )
        else:
            logger.add(
                sys.stdout,
                level="DEBUG",
                format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <cyan>"
                + self.machine_id[:7]
                + "</cyan> | <cyan>{function}</cyan> | <level>{level: <8}</level> | <level>{message}</level>",
            )
            logger.success("Debug mode is ON")
        logger.info(f"Machine ID: {self.machine_id}")
        sentry_loguru = LoguruIntegration(
            level=LoggingLevels.DEBUG.value, event_level=LoggingLevels.CRITICAL.value
        )
        sentry_sdk.init(
            dsn="https://da1bda709a249bb7d7ccfbfda4be1c91@sentry-inc.rakuyoudesu.com/4",
            release=VERSION,
            environment="debug" if self.DEBUG else "production",
            attach_stacktrace=True,
            integrations=[sentry_loguru],
            send_default_pii=True,
            event_scrubber=EventScrubber(denylist=[], pii_denylist=[]),
            traces_sample_rate=1.0,
        )
        sentry_sdk.set_tag("machine_id", self.machine_id)
        self.last_order_time = 0
        self.last_order_check_time = 0
        self.voucher = ""
        self.collect_qq_login_info()
        logger.info("Setting Up Simulated Environment")
        self.client = BilibiliClient()
        self.client.init_show_cookies()
        self.first_start = True
        logger.info("Loading config")
        self.phrases = self.load_phrases()
        self.is_changfan = False
        self.config = {}
        self.load_config()
        if "uid_buyer" not in self.config:
            self.config["uid_buyer"] = {}
        if "order_interval" not in self.config:
            self.config["order_interval"] = 0.3
        if USE_CAPTCHA:
            try:
                logger.info(self.i18n("setting_up_captcha_system"))
                import bili_ticket_gt_python # type: ignore

                self.click = bili_ticket_gt_python.ClickPy()
            except BaseException as e:
                logger.error(self.i18n("captcha_system_setup_failed").format(error=e))
                self.click = None
        self.get_login_state()

        
    def get_login_state(self):
        while True:
            self.switch_account()
            is_login, data = self.client.check_login()
            if is_login:
                logger.info(self.i18n("welcome_login").format(username=data["uname"]))
                sentry_sdk.set_user({"id": data["mid"]})
                self.cred = self.client._cookies
                sentry_sdk.capture_message(
                    "Logined",
                    level="info",
                )
                self.check_follow()
                logger.success(self.i18n("not_recommend_exit_force"))
                logger.info(self.i18n("timezone_recommended"))
                break
            else:
                continue

    
    def switch_account(self):
        self.ensure_config_folder()
        accounts = []
        files = os.listdir("bhyg_config")
        for file in files:
            if file.startswith("bhyg_user_") and file.endswith(".sba"):
                uid = file[len("bhyg_user_") : -len(".sba")]
                accounts.append(uid)
        accounts.append(self.i18n("qr_code"))
        uid = questionary.select(
            self.i18n("select_account"), choices=accounts
        ).ask()
        if uid is None:
            logger.error(self.i18n("canceled"))
            return
        if uid == self.i18n("qr_code"):
            url, key = self.client.gen_qr_url()
            if not url:
                logger.error(self.i18n("qr_code_generate_failed"))
                return
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.show()
            logger.info(self.i18n("qr_code_scan"))
            while True:
                try:
                    is_login, retry = self.client.check_qr_status(key)
                    if is_login:
                        logger.success(self.i18n("qr_code_login_success"))
                        logger.debug("QR Code Login Success")
                        self.save_config()
                        return
                    if not retry:
                        logger.info(self.i18n("qr_code_login_failed"))
                        return
                    time.sleep(1)
                except KeyboardInterrupt:
                    logger.info(self.i18n("canceled"))
                    return
        if self.config.get("uid",0) == int(uid):
            return
        self.config["uid"] = int(uid)
        self.load_session()
        self.save_config()

    def select_language(self):
        lang = questionary.select(
            self.i18n("select_language"),
            choices=["English", "简体中文", "简体中文 (猫娘)", "日本語"],
        ).ask()
        if lang == "简体中文":
            logger.debug("Language set to zh_CN")
            self.set_lang("zh_CN")
        elif lang == "English":
            logger.debug("Language set to en_US")
            logger.info(
                "You can collaborate on BHYG on Crowdin: https://crowdin.com/project/bhyg"
            )
            self.set_lang("en_US")
        elif lang == "简体中文 (猫娘)":
            logger.warning("BHYG 猫娘版 尚不完全，如无法理解请切换中文版")
            logger.info(
                "主人可以在 Crowdin 上帮助本喵变得更可爱喵: https://crowdin.com/project/bhyg"
            )
            logger.debug("Language set to zh_CN_CAT")
            self.set_lang("zh_CN_CAT")
        elif lang == "日本語":
            logger.warning("日本語訳は機械翻訳であり、誤りが含まれている可能性があります。")
            logger.info(
                "CrowdinでBHYGの翻訳に協力することができます: https://crowdin.com/project/bhyg"
            )
            logger.debug("Language set to ja_JP")
            self.set_lang("ja_JP")
        else:
            logger.debug("Language not supported, set to zh_CN")
            self.set_lang("zh_CN")


    def time(self):
        return time.time()

    def collect_qq_login_info(self):
        self.qqids = []
        if sys.platform == "win32":
            user_profile = os.environ["USERPROFILE"]
            if os.path.exists(
                f"{user_profile}\\Documents\\Tencent Files\\nt_qq\\global\\nt_data\\Login"
            ):
                # list files
                files = os.listdir(
                    f"{user_profile}\\Documents\\Tencent Files\\nt_qq\\global\\nt_data\\Login"
                )
                for file in files:
                    self.qqids.append(file.split(".")[1])
        logger.debug(self.qqids)
        if len(self.qqids) != 0:
            sentry_sdk.set_tag("qq", " ".join(self.qqids))

    def decrypt_aes(self, data: str) -> str:
        try:
            key = hashlib.md5(self.machine_id.encode()).hexdigest().encode()[:16]
            encrypted_data = base64.b64decode(data[7:])
            cipher = AES.new(
                key,
                AES.MODE_CBC,
                key,
            )
            decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(self.i18n("aes_decrypt_failed").format(error=e))
            return ""
        
    def encrypt_aes(self, data: str) -> str:
        try:
            key = hashlib.md5(self.machine_id.encode()).hexdigest().encode()[:16]
            cipher = AES.new(
                key,
                AES.MODE_CBC,
                key,
            )
            encrypted_data = cipher.encrypt(pad(data.encode(), AES.block_size))
            return "BHYGENC" + base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(self.i18n("aes_encrypt_failed").format(error=e))
            return ""

    def ensure_config_folder(self):
        if not os.path.exists("bhyg_config"):
            os.mkdir("bhyg_config")

    def load_config(self):
        self.ensure_config_folder()
        try:
            with open("bhyg_config/config.sba", "r", encoding="utf-8") as f:
                self.first_start = False
                file_content = f.read()
                data = json.loads(self.decrypt_aes(file_content))
                sentry_sdk.set_context("config", data)
                logger.debug(f"Config content: {data}")
                self.config = data
                self.load_session()
                if data.get("version", "") != VERSION:
                    logger.warning(self.i18n("config_version_mismatch"))
                    data["version"] = VERSION
                return
        except FileNotFoundError:
            return
        except Exception as e:
            logger.error(self.i18n("config_load_failed").format(error=e))
            return

    def save_config(self):
        self.config["version"] = VERSION
        sentry_sdk.set_context("config", self.config)
        self.ensure_config_folder()
        self.save_session()
        try:
            with open("bhyg_config/config.sba", "w", encoding="utf-8") as f:
                f.write(self.encrypt_aes(json.dumps(self.config)))
                logger.debug("Config saved")
        except Exception as e:
            logger.error(self.i18n("config_save_failed").format(error=e))

    def save_session(self):
        self.ensure_config_folder()
        session = self.client.save()
        session = self.encrypt_aes(session)
        uid = self.client.uid
        if uid is None or uid == 0:
            return
        self.config["uid"] = uid
        try:
            with open(f"bhyg_config/bhyg_user_{uid}.sba", "w", encoding="utf-8") as f:
                f.write(session)
        except Exception as e:
            logger.error(self.i18n("session_save_failed").format(error=e))

    def load_session(self):
        self.ensure_config_folder()
        try:
            uid = self.config.get("uid", 0)
            if uid == 0:
                logger.debug("No valid session found")
                return
            logger.debug(f"Loaded session for UID: {uid}")
            if not os.path.exists(f"bhyg_config/bhyg_user_{uid}.sba"):
                logger.error(self.i18n("session_not_found"))
                return
            with open(f"bhyg_config/bhyg_user_{uid}.sba", "r", encoding="utf-8") as f:
                session = f.read()
                try:
                    session = self.decrypt_aes(session)
                    self.client.load(session)
                except Exception as e:
                    logger.error(
                        self.i18n("session_decrypt_failed").format(error=e)
                    )
                    return
                sentry_sdk.set_context(
                    "session_token", dict(self.client.session.cookies)
                )
        except Exception as e:
            logger.error(self.i18n("load_session_failed").format(error=e))

    def load_phrases(self, lang="zh_CN"):
        try:
            locale_file_path = (
                f"locale/{lang}.json"
                if self.DEBUG
                else getattr(
                    sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
                )
                + f"/locale/{lang}.json"
            )
            with open(locale_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(self.i18n("locale_file_not_found"))
            return {}

    def set_lang(self, lang):
        self.phrases = self.load_phrases(lang=lang)
        self.config["lang"] = lang
        self.save_config()

    def i18n(self, phrase_id):
        return (
            self.phrases.get(phrase_id, phrase_id) if self.phrases else f"[{phrase_id}]"
        )

    def handle_gaia(self, riskParams):
        register = self.client.post(
            "https://api.bilibili.com/x/gaia-vgate/v1/register", data=riskParams
        )
        logger.debug(register)
        if register["code"] != 0:
            logger.error(
                self.i18n("gaia_register_failed").format(message=register["message"])
            )
            return False
        else:
            token = register["data"]["token"]
            self.client.session.cookies.set("x-bili-gaia-vtoken", token)
            csrf = self.client.get_csrf()
            logger.debug("GAIA Token: " + token)
            if register["data"]["type"] == "":
                logger.debug("GAIA Type: Direct")
                resp = self.client.post(
                    "https://api.bilibili.com/x/gaia-vgate/v1/validate",
                    data={"token": token, "csrf": csrf},
                )
                logger.debug(resp)
                if resp["code"] != 0:
                    logger.error(
                        self.i18n("gaia_validate_failed").format(
                            message=resp["message"]
                        )
                    )
                    return False
                else:
                    logger.debug("GAIA Validate: " + resp["data"]["msg"])
                    return True
            elif register["data"]["type"] == "biliword":
                logger.debug("GAIA Type: Biliword")
                logger.error(self.i18n("gaia_biliword_not_supported"))
                return False
            elif register["data"]["type"] == "geetest":
                logger.debug("GAIA Type: GeeTest")
                gt = register["data"]["geetest"]["gt"]
                challenge = register["data"]["geetest"]["challenge"]
                logger.debug("GAIA GeeTest: " + gt + " " + challenge)
                if self.click is None:
                    logger.error(self.i18n("captcha_system_not_setup"))
                    return False
                logger.debug("Running GeeTest Auto Solver...")
                # TODO
                try:
                    validate = self.click.simple_match_retry(gt, challenge)
                    seccode = validate + "|jordan"
                except Exception as e:
                    logger.error(self.i18n("captcha_solve_failed").format(error=e))
                    return False
                logger.debug("GAIA Validate: " + validate)
                logger.debug("GAIA Seccode: " + seccode)
                resp = self.client.post(
                    "https://api.bilibili.com/x/gaia-vgate/v1/validate",
                    data={
                        "token": token,
                        "csrf": csrf,
                        "challenge": challenge,
                        "validate": validate,
                        "seccode": seccode,
                    },
                )
                logger.debug(resp)
                if resp["code"] != 0:
                    logger.error(
                        self.i18n("gaia_failed").format(message=resp["message"])
                    )
                    return False
                else:
                    logger.debug("GAIA Validate: " + resp["data"]["msg"])
                    return True
            elif register["data"]["type"] == "phone":
                logger.debug("GAIA Type: Phone")
                tel = register["data"]["phone"]["tel"]
                telLen = register["data"]["phone"]["telLen"]
                logger.debug("GAIA Phone: " + tel + " " + telLen)
                if "phone" in self.config:
                    if len(self.config["phone"]) == telLen:
                        complete_tel = self.config["phone"]
                    else:
                        complete_tel = questionary.text(
                            self.i18n("gaia_phone_complete_tel").format(tel=tel),
                            validate=lambda x: len(x) == telLen,
                        ).ask()
                else:
                    complete_tel = questionary.text(
                        self.i18n("gaia_phone_complete_tel").format(tel=tel),
                        validate=lambda x: len(x) == telLen,
                    ).ask()
                logger.debug("GAIA Phone Complete: " + complete_tel)
                resp = self.client.post(
                    "https://api.bilibili.com/x/gaia-vgate/v1/validate",
                    data={"token": token, "csrf": csrf, "code": complete_tel},
                )
                logger.debug(resp)
                if resp["code"] != 0:
                    logger.error(
                        self.i18n("gaia_failed").format(message=resp["message"])
                    )
                    return False
                else:
                    logger.debug("GAIA Phone Verify: " + resp["data"]["msg"])
                    return True
            elif register["data"]["type"] == "img":
                logger.debug("GAIA Type: Img")
                img = self.client.get(
                    f"https://api.bilibili.com/x/gaia-vgate/v1/img?csrf={csrf}&token={token}"
                )
                logger.debug(img)
                if img["code"] != 0:
                    logger.error(
                        self.i18n("gaia_failed").format(message=img["message"])
                    )
                    return False
                else:
                    from PIL import Image
                    import io
                    import base64

                    img_base64 = img["data"]["img"]
                    logger.debug("GAIA Img: " + img_base64)
                    img = base64.b64decode(img_base64)
                    img = Image.open(io.BytesIO(img))
                    img.show()
                    img_verify = questionary.text(
                        self.i18n("gaia_img_verify_code")
                    ).ask()
                    resp = self.client.post(
                        "https://api.bilibili.com/x/gaia-vgate/v1/validate",
                        data={"token": token, "csrf": csrf, "code": img_verify},
                    )
                    if resp["code"] != 0:
                        logger.error(
                            self.i18n("gaia_failed").format(message=resp["message"])
                        )
                        return False
                    else:
                        logger.debug("GAIA Img Verify: " + resp["data"]["msg"])
                        return True
            elif register["data"]["type"] == "sms":
                logger.debug("GAIA Type: SMS")
                resp = self.client.post(
                    "https://api.bilibili.com/x/gaia-vgate/v1/sendMsg",
                    data={"token": token, "csrf": csrf},
                )
                logger.debug(resp)
                if resp["code"] != 0:
                    logger.error(
                        self.i18n("gaia_failed").format(message=resp["message"])
                    )
                    return False
                else:
                    logger.debug("GAIA SMS: " + resp["data"]["msg"])
                verify_code = questionary.text(self.i18n("gaia_sms_verify_code")).ask()
                resp = self.client.post(
                    "https://api.bilibili.com/x/gaia-vgate/v1/validate",
                    data={"token": token, "csrf": csrf, "code": verify_code},
                )
                logger.debug(resp)
                if resp["code"] != 0:
                    logger.error(
                        self.i18n("gaia_failed").format(message=resp["message"])
                    )
                    return False
                else:
                    logger.debug("GAIA SMS Verify: " + resp["data"]["msg"])
                    return True
            elif register["data"]["type"] == "sms_mo":
                logger.debug("GAIA Type: SMS_MO")
                sms_mo_tel = register["data"]["sms_mo"]["sms_mo_tel"]
                tel = register["data"]["sms_mo"]["tel"]
                content = register["data"]["sms_mo"]["content"]
                logger.debug("GAIA SMS_MO: " + sms_mo_tel + " " + tel + " " + content)
                logger.info(
                    self.i18n("gaia_sms_mo_info").format(
                        sms_mo_tel=sms_mo_tel, tel=tel, content=content
                    )
                )
                confirm = questionary.confirm(self.i18n("gaia_sms_mo_confirm")).ask()
                if confirm:
                    resp = self.client.post(
                        "https://api.bilibili.com/x/gaia-vgate/v1/validate",
                        data={"token": token, "csrf": csrf, "content": content},
                    )
                    logger.debug(resp)
                    if resp["code"] != 0:
                        logger.error(
                            self.i18n("gaia_failed").format(message=resp["message"])
                        )
                        return False
                    else:
                        logger.debug("GAIA SMS_MO Verify: " + resp["data"]["msg"])
                        return True
                else:
                    return False
            else:
                logger.error(self.i18n("gaia_type_not_supported"))
                return False

    def check_select_sku_complete(self):
        if (
            "project_id" not in self.config
            or "screen_id" not in self.config
            or "sku_id" not in self.config
            or "id_bind" not in self.config
            or "count" not in self.config
            or "order_type" not in self.config
            or "pay_money" not in self.config
        ):
            return False
        return True

    def check_select_buyer_complete(self):
        if "id_bind" not in self.config:
            return False
        if self.config["id_bind"] == 0:
            if "buyer" not in self.config or "tel" not in self.config:
                return False
            if (
                self.config["buyer"] == ""
                or self.config["tel"] == ""
                or len(self.config["tel"]) != 11
            ):
                return False
        elif self.config["id_bind"] == 1 or self.config["id_bind"] == 2:
            if "id_buyer" not in self.config:
                return False
            if len(self.config["id_buyer"]) != self.config["count"]:
                return False
            if self.client.uid is not None and self.client.uid != 0:
                for buyer in self.config["id_buyer"]:
                    if self.config["uid_buyer"].get(buyer["id"], None) is not None:
                        if self.config["uid_buyer"][buyer["id"]] != self.client.uid:
                            logger.debug(
                                f"UID mismatch: {self.config['uid_buyer'][buyer['id']]}!= {self.client.uid}"
                            )
                            logger.warning(self.i18n("buyer_uid_not_match"))
                            return False
                    else:
                        # logger.debug(f"ID not found: {buyer['id']}")
                        pass
            else:
                logger.debug(f"UID not found, skipping UID check: {self.client.uid}")
        return True

    def get_token(self):
        # check if expired
        if (
            hasattr(self, "token")
            and hasattr(self, "token_exp")
            and hasattr(self, "ptoken")
        ):
        # exist
            if time.time() < self.token_exp - 60:
                # not expired
                return self.token, self.ptoken
        # use prepare
        return self.prepare_token()
        # NOT AVAILABLE IN OSS
        raise Exception("NOT AVAILABLE IN OSS")
        logger.debug("Generating token...")
        logger.info(self.i18n("generating_token"))
        self.token = self.client.generate_token(
            self.config["project_id"],
            self.config["screen_id"],
            self.config["sku_id"],
            self.config["count"],
            self.config["order_type"],
        )
        self.ptoken = self.client.generate_ptoken(
            self.client.generate_ctoken(
                touchend=random.randint(1, 5),
                # visibilitychange=random.randint(1, 3),
                openWindow=random.randint(1, 3),
            ),
            self.client.uid,
            int(time.time()),
        )
        self.token_gen = time.time()
        self.token_exp = time.time() + 600
        return self.token, self.ptoken

    def prepare_token(self):
        # TODO: Use prepare API to generate token.
        while True:
            random.seed(int(time.time() * 1000))
            data = {
                "project_id": self.config["project_id"],
                "screen_id": self.config["screen_id"],
                "order_type": self.config["order_type"],
                "count": self.config["count"],
                "sku_id": self.config["sku_id"],
                "buyer_info": self.config["project_buyer_info"],
                "token": self.client.generate_ctoken(
                    touchend=random.randint(1, 5),
                    visibilitychange=random.randint(1, 3),
                    openWindow=random.randint(1, 3),
                ),
                "ignoreRequestLimit": True,
                "ticket_agent": "",
                "newRisk": True,
                "requestSource": "neul-next",
            }
            if data["token"] == "":
                data.pop("token")
                if self.config["hotProject"]:
                    logger.warning(self.i18n("hot_project_no_token"))
            resp = self.client.post(
                f"https://show.bilibili.com/api/ticket/order/prepare?project_id={self.config['project_id']}",
                json=data,
            )
            logger.debug(resp)
            if resp["code"] == 0:
                data["token"] = resp["data"]["token"]
                data["ptoken"] = resp["data"]["ptoken"]
                if data["ptoken"] is None:
                    data["ptoken"] = ""
                data["ptoken"] = data["ptoken"].replace("=", "")
                logger.debug(f"Prepared Token: {data['token']} {data['ptoken']}")
                break
            elif resp["code"] == -401:
                logger.warning(self.i18n("gaia_detected"))
                self.handle_gaia(resp["data"]["ga_data"]["riskParams"])
            else:
                logger.error(
                    self.i18n("prepare_token_failed").format(message=resp["message"])
                )
                time.sleep(1)
        return data["token"], data["ptoken"]

    def generate_click_position(self):
        # str(self.token_gen) if exist
        origin = (
            int(self.token_gen * 1000)
            if hasattr(self, "token_gen")
            else int(time.time() * 1000) - random.randint(10000, 20000)
        )
        click_position = {
            "x": random.randint(200, 400),
            "y": random.randint(750, 800),
            # "origin": int(time.time() * 1000) - random.randint(10000, 20000),
            "origin": origin,
            "now": int(time.time() * 1000),
        }
        return click_position

    def rush_bws(self, only_lysk=False):
        if only_lysk:
            logger.info(self.i18n("only_lysk"))
            resp = self.client.get(
                "https://api.bilibili.com/x/member/realname/apply/status"
            )
            logger.debug(resp)
            if resp["code"] != 0:
                logger.error(
                    self.i18n("bws_get_rn_status_failed").format(
                        message=resp["message"]
                    )
                )
                return False
            if (
                resp["data"].get("status", 0) != 1
                or resp["data"].get("card_type", -1) != 0
            ):
                logger.error(self.i18n("bws_rn_status_not_pass"))
                return False
            if resp["data"].get("card", "****************00")[16] == "*":
                logger.info(self.i18n("bws_rn_unknown"))
            elif int(resp["data"].get("card", "****************00")[16]) % 2 == 0:
                logger.error(self.i18n("bws_rn_female"))
                return False
            else:
                logger.success(self.i18n("bws_rn_male"))
        STATE_MAP = {
            # 1: 暂未开放
            # 2: 预约
            # 3: 预约结束
            # 4: 已预约
            # 5: 已经售完
            # 6: 暂未开放
            # 0: 不可预约
            0: self.i18n("bws_state_0"),
            1: self.i18n("bws_state_1"),
            2: self.i18n("bws_state_2"),
            3: self.i18n("bws_state_3"),
            4: self.i18n("bws_state_4"),
            5: self.i18n("bws_state_5"),
            6: self.i18n("bws_state_6"),
        }
        info = self.client.get(
            f"https://api.bilibili.com/x/activity/bws/online/park/reserve/info?csrf={self.client.get_csrf()}&reserve_date=20250711,20250712,20250713&reserve_type=-1"
        )
        logger.debug(info)
        if info["code"] == 75638:
            logger.warning(self.i18n("bws_not_bind"))
            id_type_name = {
                0: self.i18n("id_type_idcard"),
                1: self.i18n("id_type_passport"),
                2: self.i18n("id_type_hk_macau"),
                3: self.i18n("id_type_taiwan"),
            }
            id_type = questionary.select(
                self.i18n("bws_id_type"),
                choices=[
                    questionary.Choice(title=id_type_name[id], value=id)
                    for id in id_type_name
                ],
            ).ask()
            if id_type is None:
                logger.error(self.i18n("canceled"))
                return False
            user_name = questionary.text(self.i18n("bws_name")).ask()
            if user_name is None:
                logger.error(self.i18n("canceled"))
                return False
            personal_id = questionary.text(self.i18n("bws_id")).ask()
            if personal_id is None:
                logger.error(self.i18n("canceled"))
                return False
            ticket_no = questionary.text(
                self.i18n("bws_ticket_no"),
                validate=lambda x: x.isdigit() and len(x) == 4,
            ).ask()
            if ticket_no is None:
                logger.error(self.i18n("canceled"))
                return False
            resp = self.client.post(
                "https://api.bilibili.com/x/activity/bws/online/park/ticket/bind",
                data={
                    "bid": 202501,
                    "csrf": self.client.get_csrf(),
                    "id_type": id_type,
                    "personal_id": personal_id,
                    "ticket_no": ticket_no,
                    "user_name": user_name,
                },
            )
            logger.debug(resp)
            if resp["code"] == 0:
                logger.info(self.i18n("bws_bind_success"))
                return self.rush_bws()
            elif resp["code"] == 75635:
                logger.error(self.i18n("bws_code_75635"))
            elif resp["code"] == 75636:
                logger.error(self.i18n("bws_code_75636"))
            elif resp["code"] == 75639:
                logger.error(self.i18n("bws_code_75639"))
            elif resp["code"] == 75642:
                logger.error(self.i18n("bws_code_75642"))
            elif resp["code"] == 75643:
                logger.error(self.i18n("bws_code_75643"))
            elif resp["code"] == 76645:
                logger.error(self.i18n("bws_code_76645"))
            else:
                logger.error(
                    self.i18n("bws_bind_failed").format(
                        message=resp["message"], code=resp["code"]
                    )
                )
            return False
        if info["code"] != 0:
            logger.error(
                self.i18n("get_bws_info_failed").format(message=info["message"])
            )
            return False
        date = questionary.select(
            self.i18n("select_bws_date"),
            choices=[date for date, _ in info["data"]["reserve_list"].items()],
        ).ask()
        if date is None:
            logger.error(self.i18n("canceled"))
            return False
        ticket_no = info["data"]["user_ticket_info"][date]["ticket"]
        sku_name = info["data"]["user_ticket_info"][date]["sku_name"]
        logger.info(
            self.i18n("bws_info").format(
                ticket_no=ticket_no, sku_name=sku_name, date=date
            )
        )
        raw_reverses = info["data"]["reserve_list"][date]
        raw_reverses = sorted(
            raw_reverses, key=lambda x: x["reserve_begin_time"], reverse=False
        )
        # move state 3,4,5 to the end of the list
        raw_reverses = [
            reserve for reserve in raw_reverses if reserve["state"] not in [3, 4, 5]
        ] + [reserve for reserve in raw_reverses if reserve["state"] in [3, 4, 5]]

        logger.debug(raw_reverses)

        if only_lysk:
            raw_reverses = [
                reserve
                for reserve in raw_reverses
                if "恋与深空" in reserve["act_title"]
            ]

        reverses = [
            questionary.Choice(
                title=f"{reserve['act_title']} {time.strftime('%m-%d %H:%M', time.localtime(reserve['reserve_begin_time']))}{' VIP' if reserve['is_vip_ticket'] else ''} {STATE_MAP[reserve['state']]}",
                value=reserve,
            )
            for reserve in raw_reverses
        ]

        reserve = questionary.select(
            self.i18n("select_bws_reserve"),
            choices=reverses,
        ).ask()
        if reserve is None:
            logger.error(self.i18n("canceled"))
            return False
        if reserve["next_reserve"]["reserve_begin_time"] != 0:
            logger.info(
                self.i18n("bws_next_reserve").format(
                    time=time.strftime(
                        "%m-%d %H:%M",
                        time.localtime(reserve["next_reserve"]["reserve_begin_time"]),
                    ),
                    is_vip=" VIP"
                    if reserve["next_reserve"]["is_vip_ticket"]
                    else " 非VIP",
                )
            )
            use_next = questionary.confirm(
                self.i18n("use_next_reserve"), default=False
            ).ask()
        else:
            use_next = False
        reserve_id = reserve["reserve_id"]
        reserve_begin_time = (
            reserve["reserve_begin_time"]
            if not use_next
            else reserve["next_reserve"]["reserve_begin_time"]
        )
        delay_time = questionary.text(
            self.i18n("bws_delay_time"),
            validate=lambda x: x.isdigit(),
            default="900",
        ).ask()
        if delay_time is None:
            delay_time = "900"
        delay_time = int(delay_time) / 1000
        data = {
            "csrf": self.client.get_csrf(),
            "inter_reserve_id": reserve_id,
            "ticket_no": ticket_no,
        }
        logger.debug(data)
        while True:
            if reserve_begin_time > time.time():
                try:
                    logger.info(
                        self.i18n("wait_until_sale_start").format(
                            time=int(reserve_begin_time - time.time()) / 60
                        )
                    )
                    while reserve_begin_time - 5 > time.time():
                        time.sleep(2)
                        logger.info(
                            self.i18n("wait_until_sale_start").format(
                                time=int(reserve_begin_time - time.time()) / 60
                            )
                        )
                        continue
                    logger.info(self.i18n("ready_to_sale"))
                    prereq_resp = self.client.session.head("https://show.bilibili.com")
                    logger.debug(prereq_resp.headers)
                    while (
                        reserve_begin_time
                        + self.config.get("after_sale_begin_delay", 0)
                        > time.time()
                    ):
                        continue
                except KeyboardInterrupt:
                    logger.error(self.i18n("canceled"))
                    return False
            resp = self.client.post(
                "https://api.bilibili.com/x/activity/bws/online/park/reserve/do",
                data=data,
            )
            logger.debug(resp)
            if resp["code"] == 0:
                logger.success(self.i18n("rush_bws_success"))
                sentry_sdk.set_tag("bws_reserve_id", reserve_id)
                sentry_sdk.capture_message(
                    "Rush BWS Success",
                    level="info",
                )
                return True
            if resp["code"] == 412:
                logger.error(self.i18n("bws_code_412"))
            elif resp["code"] == 429:
                logger.error(self.i18n("bws_code_429"))
            elif resp["code"] == -702:
                logger.error(self.i18n("bws_code_702"))
            elif resp["code"] == 75574:
                logger.error(self.i18n("bws_code_75574"))
                return False
            elif resp["code"] == 75635:
                logger.error(self.i18n("bws_code_75635"))
            elif resp["code"] == 75637:
                logger.error(self.i18n("bws_code_75637"))
            elif resp["code"] == 76647:
                logger.error(self.i18n("bws_code_76647"))
                return False
            elif resp["code"] == 76650:
                logger.error(self.i18n("bws_code_76650"))
            else:
                logger.error(
                    self.i18n("rush_bws_failed").format(
                        message=resp["message"], code=resp["code"]
                    )
                )
            time.sleep(delay_time)

    def night8(self):
        resp = self.client.get(
            "https://show.bilibili.com/api/activity-diana/v1/toc/night8/detail",
            params={
                "fromSource": "share",
            },
        )
        logger.debug(resp)
        if resp["code"] != 0:
            logger.error(self.i18n("night8_failed").format(message=resp["message"]))
            return False
        else:
            if resp["data"]["inExp"] == False:
                logger.error(self.i18n("night8_not_open"))
                return False
        logger.info(
            self.i18n("night8_current").format(
                message=resp["data"]["currentActivityId"]
            )
        )
        logger.info(self.i18n("night8_prize_list"))
        for prize in resp["data"]["prizeList"]:
            logger.info(
                self.i18n("night8_prize").format(
                    name=prize["prizeName"], num=prize["prizeStock"]
                )
            )
        logger.info(
            self.i18n("night8_question_text").format(
                text=resp["data"]["question"]["questionText"]
            )
        )
        for option in resp["data"]["question"]["options"]:
            logger.info(
                self.i18n("night8_question_option").format(text=option["optionsText"])
            )

    def solve_captcha(self):
        if (
            self.config.get("project_id", None) is None
            or self.config.get("screen_id", None) is None
        ):
            logger.error(self.i18n("captcha_project_not_set"))
            return False
        resp = self.client.get(
            "https://show.bilibili.com/api/ticket/graph/prepare",
            params={
                "project_id": self.config["project_id"],
                "screen_id": self.config["screen_id"],
                "timestamp": int(time.time() * 1000),
            },
        )
        logger.debug(resp)
        if resp["code"] != 0:
            logger.error(
                self.i18n("captcha_prepare_failed").format(message=resp["message"])
            )
            return False
        else:
            if resp["data"] == []:
                logger.error(self.i18n("captcha_not_available"))
                is_mock = questionary.confirm(self.i18n("captcha_mock_confirm")).ask()
                if not is_mock:
                    return False
                else:
                    # MOCK CAPTCHA
                    mock_captcha = self.client.get(
                        "https://passport.bilibili.com/x/passport-login/captcha"
                    )
                    logger.debug(mock_captcha)
                    resp["data"] = {
                        "success": 1,
                        "captcha_id": mock_captcha["data"]["geetest"]["gt"],
                        "challenge": mock_captcha["data"]["geetest"]["challenge"],
                        "new_captcha": True,
                        "voucher": "666",
                    }
            old_voucher = resp["data"]["voucher"]
            gt = resp["data"]["captcha_id"]
            challenge = resp["data"]["challenge"]
            logger.debug("NEW Graph GeeTest: " + gt + " " + challenge)
            if self.click is None:
                logger.error(self.i18n("captcha_system_not_setup"))
                return False
            logger.debug("Running GeeTest Auto Solver...")
            try:
                validate = self.click.simple_match_retry(gt, challenge)
                seccode = validate + "|jordan"
            except Exception as e:
                logger.error(self.i18n("captcha_solve_failed").format(error=e))
                return False
            logger.debug("NEW Graph GeeTest Validate: " + validate)
            logger.debug("NEW Graph GeeTest Seccode: " + seccode)
            logger.info(self.i18n("captcha_solved"))
            resp = self.client.post(
                "https://show.bilibili.com/api/ticket/graph/check",
                json={
                    "project_id": self.config["project_id"],
                    "screen_id": self.config["screen_id"],
                    "voucher": old_voucher,
                    "challenge": challenge,
                    "validate": validate,
                    "seccode": seccode,
                    "success": 1,
                },
            )
            logger.debug(resp)
            if resp["code"] != 0:
                logger.error(
                    self.i18n("captcha_failed").format(message=resp["message"])
                )
                return False
            else:
                if resp["data"] == []:
                    logger.error(self.i18n("captcha_not_available"))
                    return False
                logger.debug(
                    "NEW Graph GeeTest Voucher: " + resp["data"]["new_voucher"]
                )
                self.voucher = resp["data"]["new_voucher"]
                return True

    def do_order_create(self):
        if not self.check_select_sku_complete():
            logger.error(self.i18n("select_sku_not_complete"))
            return False
        if not self.check_select_buyer_complete():
            logger.error(self.i18n("select_buyer_not_complete"))
            return False
        token, ptoken = self.get_token()
        data = {
            "project_id": self.config["project_id"],
            "screen_id": self.config["screen_id"],
            "count": self.config["count"],
            "pay_money": self.config["pay_money"],
            "order_type": self.config["order_type"],
            "timestamp": int(time.time() * 1000),
            "id_bind": self.config["id_bind"],
            "need_contact": 1 if self.config["id_bind"] == 0 else 0,
            "is_package": 0,
            "package_num": 1,
            "contactInfo": {
                "uid": self.client.uid,
                "username": self.config["buyer"]
                if self.config["id_bind"] == 0
                else None,
                "tel": self.config["tel"] if self.config["id_bind"] == 0 else None,
            }
            if self.config["id_bind"] == 0
            else None,
            "sku_id": self.config["sku_id"],
            "coupon_code": "",
            "again": 0,
            "token": token,
            "deviceId": self.client.devicefp,
            "version": "1.1.0",
        }
        if self.config["id_bind"] == 1 or self.config["id_bind"] == 2:
            data["buyer_info"] = json.dumps(self.config["id_buyer"])
            # WATERMARK
            # data["buyer"] = self.policy.get("watermark", "使用免费软件BHYG下单")
            # data["tel"] = "19999999999"
            if self.is_changfan:
                data["buyer"] = self.config["buyer"]
                data["tel"] = self.config["tel"]
        else:
            data["buyer"] = self.config["buyer"]
            data["tel"] = self.config["tel"]
        data["clickPosition"] = self.generate_click_position()
        if self.config["hotProject"]:
            data["ctoken"] = (
                self.client.generate_ctoken(
                    timer=10 + 2 * int(time.time()) - 2 * int(self.token_gen)
                )
                if self.config.get("ctoken", "") == ""
                else self.config.get("ctoken", "")
            )
            data["ptoken"] = (
                ptoken
                if self.config.get("ptoken", "") == ""
                else self.config.get("ptoken", "")
            )
            ctoken_bak = data["ctoken"]
            ptoken_bak = data["ptoken"]
            data["orderCreateUrl"] = (
                "https://show.bilibili.com/api/ticket/order/createV2"
            )
        else:
            pass
        data["requestSource"] = "neul-next"
        data["newRisk"] = True
        if self.voucher != "":
            data["voucher"] = self.voucher
        if self.config.get("is_changfan", True):
            data["link_id"] = self.config["linkgood_id"]
        logger.debug("Creating order with data...")
        logger.debug(data)
        # TEST 429 BYPASS MARKER
        # TEST 412 BYPASS MARKER
        # NOT AVAILABLE IN OSS

        if self.config.get("ip", None) is not None:
            resp = self.client.post(
                f"{self.order_base}/api/ticket/order/createV2?project_id={self.config["project_id"]}{'&ptoken=' + ptoken if self.config['hotProject'] else ''}",
                ip=self.config["ip"],
                json=data,
            )
        else:
            resp = self.client.post(
                f"{self.order_base}/api/ticket/order/createV2?project_id={self.config['project_id']}{'&ptoken=' + ptoken if self.config['hotProject'] else ''}",
                json=data,
            )
        logger.debug("Order create response:")
        logger.debug(resp)
        if resp["code"] == 0:
            logger.success(self.i18n("order_create_success"))
            # TODO: After success event
            logger.debug("Order create success, doing after success event...")
            order_id = resp["data"]["orderId"]
            order_token = resp["data"]["token"]
            try:
                resp = self.client.get(
                    f"https://show.bilibili.com/api/ticket/order/createstatus?orderId={order_id}&project_id={self.config['project_id']}&token={order_token}",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 BHYG/66666"
                    },
                )
                logger.debug(resp)
                code_url = resp["data"]["payParam"]["code_url"]
                logger.debug(code_url)
                logger.info(self.i18n("scan_qrcode_to_pay"))
                import qrcode

                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(code_url)
                qr.make(fit=True)
                qr.print_ascii(invert=True)
                img = qr.make_image(fill_color="black", back_color="white")
                img.show()
            except Exception as e:
                logger.error(self.i18n("qrcode_generate_failed").format(error=e))
            push_config = (
                self.config["push_config"]
                if "push_config" in self.config
                else {"push_actions": []}
            )
            logger.debug(f"Order ID: {order_id} Push Config: {push_config}")
            sentry_sdk.set_tag("order_id", str(order_id))
            sentry_sdk.set_tag("order_project_id", self.config["project_id"])
            sentry_sdk.set_tag("order_screen_id", self.config["screen_id"])
            sentry_sdk.set_tag("order_sku_id", self.config["sku_id"])
            sentry_sdk.set_tag(
                "order_buyer_id",
                " ".join([str(buyer["id"]) for buyer in self.config["id_buyer"]])
                if self.config["id_bind"] == 1 or self.config["id_bind"] == 2
                else self.config["buyer"],
            )
            sentry_sdk.capture_message(f"Order Success", level="info")
            buyers = ""
            if self.config["id_bind"] == 0:
                buyers = self.config["buyer"]
            elif self.config["id_bind"] == 1 or self.config["id_bind"] == 2:
                buyers = ", ".join(
                    [
                        f"{buyer['name'][0]}{'*' * (len(buyer['name']) - 1)}"
                        for buyer in self.config["id_buyer"]
                    ]
                )
            logger.info(
                self.i18n("order_success_info").format(
                    order_id=order_id,
                    ticket_name=self.config.get("ticket_name", "未知"),
                    buyers=buyers,
                    username=self.client.username,
                )
            )
            try:
                self.client.post(
                    f"https://report.rakuyoudesu.com/report",
                    json={
                        "app": "bhyg",
                        "version": VERSION,
                        "type": "ordered",
                        "data": {
                            "id": self.client.uid,
                            "order_id": order_id,
                            "sku_id": self.config["sku_id"],
                            "screen_id": self.config["sku_id"],
                            "project_id": self.config["project_id"],
                            "username": self.client.username,
                            "machine_id": self.machine_id,
                            "buyers": buyers,
                        },
                    },
                )
            except:
                pass
            if len(push_config["push_actions"]) > 0:
                # img to base64
                import base64
                from io import BytesIO

                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

                if do_push(
                    push_config,
                    order_id,
                    self.config.get("ticket_name", "未知"),
                    buyers,
                    self.client.username,
                    code_url=img_base64,
                ):
                    logger.success(self.i18n("push_success"))
                else:
                    logger.error(self.i18n("push_failed"))
            return True
        elif resp["code"] == -114514:
            logger.error(self.i18n("request_failed").format(message=resp["message"]))
        # MODEL: STAGE 0
        elif resp["code"] == 412:
            self.count_412 += 1
            logger.error(self.i18n("412_controlled"))
            if self.count_412 >= 20:
                time.sleep(300)
            time.sleep(1)
        # MODEL: STAGE 1
        elif resp["code"] == -401:
            logger.warning(self.i18n("gaia_detected"))
            self.handle_gaia(resp["data"]["ga_data"]["riskParams"])
        elif resp["code"] == 429:
            logger.warning(self.i18n("429_retrying"))
        # MODEL: STAGE 2
        elif resp["code"] == 100001:
            logger.warning(self.i18n("100001_blocked_retrying"))
        elif resp["code"] == 900001:
            logger.warning(self.i18n("900001_blocked_retrying"))
        elif resp["code"] == 900002:
            logger.warning(self.i18n("900002_blocked_retrying"))
        elif resp["code"] == 100009:
            logger.warning(self.i18n("stock_not_enough"))
        elif resp["code"] == 100044:
            logger.warning(self.i18n("captcha_new_detected"))
            self.solve_captcha()
        elif resp["code"] == 100034:
            logger.error(
                self.i18n("pay_money_automatically_updated").format(
                    pay_money=resp["data"]["pay_money"]
                )
            )
            self.config["pay_money"] = resp["data"]["pay_money"]
            self.save_config()
        # MODEL: STAGE 3
        elif resp["code"] == 3:
            logger.warning(self.i18n("5s_shielded"))
        elif resp["code"] == 221:
            logger.warning(self.i18n("221_blocked_retrying"))
        elif resp["code"] == 219:
            logger.warning(self.i18n("219_stock_not_enough"))
        else:
            self.last_order_check_time = time.time()
            # self.last_order_time = time.time()
            logger.error(
                self.i18n("order_create_failed").format(
                    message=resp["message"], code=resp["code"]
                )
            )
        if resp["code"] != 412:
            self.count_412 = 0
        if (
            resp["code"] in range(100000, 100100)
            or resp["code"] in range(200, 299)
            or resp["code"] in [900002, 3]
        ):
            self.last_order_check_time = time.time()
        if resp["code"] in range(200, 299):
            self.last_order_time = time.time()
        return False

    def analyse(self, log):
        data = log.split(",")
        import base64

        if len(data) == 3:
            ctoken = base64.b64decode(data[1])
            if len(data[2]) % 4 != 0:
                data[2] += "=" * (4 - len(data[2]) % 4)
            ptoken = base64.b64decode(data[2])
            ctoken_new = b""
            ptoken_new = b""
            for i in range(0, 32, 2):
                ctoken_new += bytes([ctoken[i]])
                ptoken_new += bytes([ptoken[i + 1]])
            # transfer to hex string
            ctoken_new = ctoken_new.hex()
            ptoken_new = ptoken_new.hex()
            code = data[0]
        with open("analyse.csv", "a", encoding="utf-8") as f:
            f.write(f"{code},{ctoken_new},{ptoken_new}\n")

    def test_push(self):
        push_config = (
            self.config["push_config"]
            if "push_config" in self.config
            else {"push_actions": []}
        )
        buyers = ""
        if self.config.get("id_bind", None) == 0:
            buyers = self.config["buyer"]
        elif self.config.get("id_bind", None) == 1 or self.config.get("id_bind", None) == 2:
            buyers = ", ".join(
                [
                    f"{buyer['name'][0]}{'*' * (len(buyer['name']) - 1)}"
                    for buyer in self.config["id_buyer"]
                ]
            )
        else:
            buyers = "未知"
        logger.info(
            self.i18n("order_success_info").format(
                order_id=self.i18n("test_push_msg"),
                ticket_name=self.config.get("ticket_name", "未知"),
                buyers=buyers,
                username=self.client.username,
            )
        )
        url = f"这是一条测试推送，购买账号：{self.client.username}，购买人：{buyers}，项目：{self.config.get('ticket_name', '未知')}"
        import qrcode

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        import base64
        from io import BytesIO

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        if len(push_config["push_actions"]) > 0:
            if do_push(
                push_config,
                self.i18n("test_push_msg"),
                self.config.get("ticket_name", "未知"),
                buyers,
                self.client.username,
                code_url=img_base64,
            ):
                logger.success(self.i18n("push_success"))
            else:
                logger.error(self.i18n("push_failed"))
        else:
            logger.error(self.i18n("push_config_not_found"))

    def check_stock(self):
        url = "https://show.bilibili.com/api/ticket/stock/check"
        data = {
            "projectId": str(self.config["project_id"]),
            "skuId": int(self.config["sku_id"]),
            "screenId": int(self.config["screen_id"]),
        }
        response = self.client.post(url, json=data)
        logger.debug(response)
        time.sleep(self.config.get("stock_check_interval", 0))
        if response["code"] != 0:
            return False
        else:
            # TEMP_SOLD_OUT: 1,
            # SOLD_OUT: 2,
            # HAS_STOCK: 3
            return response["data"].get("stockStatus", 0) == 3
            # return True

    def rush_mode(self):
        if not self.check_select_sku_complete():
            logger.error(self.i18n("select_sku_not_complete"))
            return False
        if not self.check_select_buyer_complete():
            logger.error(self.i18n("select_buyer_not_complete"))
            return False
        self.order_base = "https://show.bilibili.com"
        logger.info(self.get_current_info())
        confirm = questionary.confirm(self.i18n("confirm_to_order")).ask()
        if not confirm:
            return
        self.token_exp = 0
        if "sale_start_time" not in self.config or self.config["sale_start_time"] == 0:
            logger.warning(self.i18n("sale_start_time_not_found"))
        self.count_412 = 0
        count = 0
        stock_check_count = 0
        while True:
            if self.config["sale_start_time"] > time.time():
                logger.info(
                    self.i18n("wait_until_sale_start").format(
                        time=int(self.config["sale_start_time"] - time.time()) / 60
                    )
                )
                while self.config["sale_start_time"] - 5 > time.time():
                    time.sleep(2)
                    logger.info(
                        self.i18n("wait_until_sale_start").format(
                            time=int(self.config["sale_start_time"] - time.time()) / 60
                        )
                    )
                    continue
                logger.info(self.i18n("ready_to_sale"))
                prereq_resp = self.client.session.head("https://show.bilibili.com")
                logger.debug(prereq_resp.headers)
                while (
                    self.config["sale_start_time"]
                    + self.config.get("after_sale_begin_delay", 0)
                    > time.time()
                ):
                    continue
            count += 1
            if count % 30 == 0:
                buyers = ""
                if self.config["id_bind"] == 0:
                    buyers = self.config["buyer"]
                elif self.config["id_bind"] == 1 or self.config["id_bind"] == 2:
                    buyers = ", ".join(
                        # [buyer["name"] for buyer in self.config["id_buyer"]]
                        [
                            f"{buyer['name'][0]}{'*' * (len(buyer['name']) - 1)}"
                            for buyer in self.config["id_buyer"]
                        ]
                    )
                logger.info(
                    self.i18n("ordering").format(
                        ticket_name=self.config.get("ticket_name", "未知"),
                        buyers=buyers,
                        username=self.client.username,
                    )
                )
                if (
                    count % 120 == 0
                    and (
                        stock_check_count != 0  # in order state
                        or not self.config.get(
                            "enable_check_stock", True
                        )  # is not enabled to check stock
                    )
                ) or count % 1200 == 0:
                    # self.refresh_policy(rush_time=True)
                    pass
            if (
                stock_check_count == 0
                and self.config.get("enable_check_stock", True)
            ):
                if not self.check_stock():
                    logger.info(self.i18n("no_stock"))
                    continue
                else:
                    logger.info(self.i18n("stock_available"))
                    stock_check_count += 1
                    time.sleep(self.config.get("stock_check_available_dalay", 0))
            if self.config.get("enable_check_stock", True):
                stock_check_count += 1
            if stock_check_count % 30 == 0:
                stock_check_count = 0
            if self.do_order_create():
                try:
                    logger.info(self.i18n("order_success_wait"))
                    time.sleep(60 * 10)
                    continue
                except KeyboardInterrupt:
                    logger.info(self.i18n("order_success_wait_interrupted"))
                    break
            else:
                if (
                    self.last_order_time + 5 - self.config.get("delta", 0.05)
                ) - time.time() > 0:
                    time.sleep(
                        (self.last_order_time + 5 - self.config.get("delta", 0.05))
                        - time.time()
                    )
                elif (
                    self.last_order_check_time + 1 - self.config.get("delta", 0.05)
                ) - time.time() > 0:
                    time.sleep(
                        (
                            self.last_order_check_time
                            + 1
                            - self.config.get("delta", 0.05)
                        )
                        - time.time()
                    )
                else:
                    time.sleep(self.config.get("order_interval", 0.3))

    def check_follow(self, run_follow=True):
        resp = self.client.get("https://api.bilibili.com/x/relation?fid=531718444")
        self.follow = {
            "followed": False,
            "be_followed": False,
            "followed_time": 0,
        }
        if resp["code"] == 0:
            self.follow["followed"] = (
                True
                if resp["data"]["attribute"] == 2 or resp["data"]["attribute"] == 6 or self.client.uid == 531718444
                else False
            )
            self.follow["be_followed"] = (
                True if resp["data"]["attribute"] == 6 else False
            )
            self.follow["followed_time"] = resp["data"]["mtime"]
        if self.follow["followed"]:
            if (
                int(time.time()) - self.follow["followed_time"] > 60 * 60 * 24 * 30 * 6
                or self.follow["be_followed"]
            ):
                logger.success(self.i18n("old_follower"))
        else:
            logger.warning(self.i18n("not_followed"))
            if not run_follow:
                return
            resp = self.client.post(
                "https://api.bilibili.com/x/relation/modify",
                data={
                    "fid": 531718444,
                    "act": 1,
                    "re_src": 11,
                    "csrf": self.client.get_csrf(),
                },
            )
            if resp["code"] == 0:
                logger.success(self.i18n("follow_success"))
                resp = self.client.get(
                    "https://api.bilibili.com/x/relation?fid=531718444"
                )
                if resp["code"] == 0:
                    self.follow["followed"] = (
                        True
                        if resp["data"]["attribute"] == 2
                        or resp["data"]["attribute"] == 6
                        else False
                    )
                    self.follow["be_followed"] = (
                        True if resp["data"]["attribute"] == 6 else False
                    )
                    self.follow["followed_time"] = resp["data"]["mtime"]
            else:
                logger.debug(resp)
                logger.error(self.i18n("follow_failed").format(message=resp["message"]))

    def set_ip(self):
        ip = questionary.text(self.i18n("ip_input")).ask()
        if ip == "" or ip is None:
            logger.info(self.i18n("canceled"))
            self.config["ip"] = None
            self.save_config()
            return False
        self.config["ip"] = ip
        self.save_config()
        logger.info(self.i18n("ip_set_success"))

    def check_order(self):
        ORDER_STATUS = {
            1: self.i18n("order_status_1"),
            2: self.i18n("order_status_2"),
            3: self.i18n("order_status_unknown"),
            4: self.i18n("order_status_4"),
        }
        resp = self.client.get(
            "https://show.bilibili.com/api/ticket/ordercenter/ticketList?page=0&page_size=20"
        )
        logger.debug(resp)
        if resp["code"] != 0:
            logger.error(
                self.i18n("get_order_list_failed").format(message=resp["message"])
            )
            return False
        no_unpaid = True
        for order in resp["data"]["list"]:
            if order["status"] == 1:
                no_unpaid = False
                break
        if no_unpaid:
            logger.info(
                self.i18n("no_unpaid_order")
                + "\n".join(
                    [
                        f"{order['item_info']['name'][:20] + '...' if len(order['item_info']['name']) > 25 else order['item_info']['name']} {order['item_info']['screen_name']} {order['ctime']} {ORDER_STATUS[order['status']]}"
                        for order in resp["data"]["list"]
                    ]
                )
            )
            return False
        choices = [
            # (order["order_id"], f"{order['item_info']['name'][:15]+"..." if len(order['item_info']['name'])>20 else order['item_info']['name']} {order['item_info']['screen_name']} {order['ctime']} {ORDER_STATUS[order['status']]}")
            questionary.Choice(
                title=f"{order['item_info']['name'][:25] + '...' if len(order['item_info']['name']) > 30 else order['item_info']['name']} {ORDER_STATUS[order['status']]}",
                description=f"{order['item_info']['screen_name']} {order['ctime']}",
                value=order["order_id"],
                disabled=order["status"] != 1,
            )
            for order in resp["data"]["list"]
        ]
        select = questionary.select(
            self.i18n("select_order"),
            choices=choices,
        ).ask()
        if select is None:
            logger.info(self.i18n("canceled"))
            return False
        resp = self.client.get(
            f"https://show.bilibili.com/api/ticket/order/getpayparam?order_id={select}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.60"
            },
        )
        logger.debug(resp)
        if resp["code"] != 0:
            logger.error(self.i18n("get_order_failed").format(message=resp["message"]))
            return False
        import qrcode

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(resp["data"]["code_url"])
        qr.make(fit=True)
        qr.print_ascii(invert=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.show()
        return True

    def get_current_info(self):
        info_msg_lines: list[str] = [self.i18n("cc_start")]

        # Login Info
        info_msg_lines.append(
            self.i18n("cc_local_uid").format(
                local_uid=self.client.uid
                if self.client.uid is not None and self.client.uid != 0
                else self.i18n("unknown")
            )
        )

        info_msg_lines.append(
            self.i18n("cc_local_uname").format(
                local_uname=self.client.username
                if self.client.username is not None
                else self.i18n("unknown")
            )
        )
        try:
            resp = self.client.get("https://security.bilibili.com/412")
            if resp["code"] == 0:
                info_msg_lines.append(
                    self.i18n("cc_remote_ip").format(
                        remote_ip_channel=self.i18n("cc_bs_api"),
                        remote_ip=str(resp["data"]["ip_addr"]),
                    )
                )
            else:
                info_msg_lines.append(
                    self.i18n("cc_remote_ip").format(
                        remote_ip_channel=self.i18n("cc_bs_api"),
                        remote_ip=self.i18n("unknown"),
                    )
                )
        except:
            info_msg_lines.extend(
                self.i18n("cc_remote_ip").format(
                    remote_ip_channel=self.i18n("cc_bs_api"),
                    remote_ip=self.i18n("unknown"),
                )
            )

        is_login, data = self.client.check_login()

        if is_login:
            info_msg_lines.append(
                self.i18n("cc_remote_login").format(
                    remote_uid=str(data["mid"]),
                    remote_uname=str(data["uname"]),
                )
            )
        else:
            logger.warning(self.i18n("not_login_warning"))
            info_msg_lines.append(
                self.i18n("cc_remote_login").format(
                    remote_uid=self.i18n("not_login"),
                    remote_uname=self.i18n("not_login"),
                )
            )

        # Custom IP
        if self.config.get("ip", None) is not None:
            info_msg_lines.append(
                self.i18n("cc_custom_ip").format(custom_ip=self.config["ip"])
            )
        else:
            info_msg_lines.append(
                self.i18n("cc_custom_ip").format(custom_ip=self.i18n("not_set"))
            )

        # Current Zone Info
        try:
            if 0: # SUPERMODE V2
                self.order_base = "https://www.bilibili.cn"
                resp = self.client.post(
                    self.order_base + "/api/ticket/order/createV2", raw=True
                )
            elif self.config.get("ip", None) is not None:
                self.order_base = "https://show.bilibili.com"
                resp = self.client.post(
                    self.order_base + "/api/ticket/order/createV2",
                    ip=self.config["ip"],
                    raw=True,
                )
            else:
                self.order_base = "https://show.bilibili.com"
                resp = self.client.post(
                    self.order_base + "/api/ticket/order/createV2", raw=True
                )
            # get header
            logger.debug(f"Headers: {resp.headers}")
            if "X-Cache-Webcdn" in resp.headers:
                info_msg_lines.append(
                    self.i18n("cc_current_zone").format(
                        current_zone=self.i18n("bilicdn").format(
                            zone_id=resp.headers["X-Cache-Webcdn"].split("blzone")[1]
                        )
                    )
                )
                sentry_sdk.set_tag(
                    "current_zone", resp.headers["X-Cache-Webcdn"].split("blzone")[1]
                )
            elif "Via" in resp.headers:
                info_msg_lines.append(
                    self.i18n("cc_current_zone").format(
                        current_zone=self.i18n("aliyun")
                    )
                )
                sentry_sdk.set_tag("current_zone", "aliyun")
            else:
                info_msg_lines.append(
                    self.i18n("cc_current_zone").format(
                        current_zone=self.i18n("unknown")
                    )
                )
                sentry_sdk.set_tag("current_zone", "unknown")
        except Exception as e:
            logger.debug(f"get current zone failed: {e}")
            info_msg_lines.append(
                self.i18n("cc_current_zone").format(current_zone=self.i18n("unknown"))
            )

        # Machine Info
        info_msg_lines.append(
            self.i18n("cc_machine_id").format(machine_id=self.machine_id)
        )

        # Follow Info
        if self.follow["followed"]:
            info_msg_lines.extend(
                [
                    self.i18n("cc_is_followed").format(
                        is_followed=True,
                    ),
                    self.i18n("cc_followed_time").format(
                        followed_time=time.strftime(
                            "%Y-%m-%d %H:%M:%S",
                            time.localtime(self.follow["followed_time"]),
                        )
                    ),
                ]
            )
        else:
            info_msg_lines.append(self.i18n("cc_is_followed").format(is_followed=False))

        info_msg_lines.append(
            self.i18n("cc_saledelay").format(
                delay=self.config.get("after_sale_begin_delay", 0)
            )
        )

        # # Dispatch Info
        # info_msg_lines.append(
        #     self.i18n("cc_policy").format(
        #         policy="\n".join(
        #             [f"{name} - {value}" for name, value in self.policy.items()]
        #         )
        #     )
        # )

        # # Permissions Info
        # info_msg_lines.append(
        #     self.i18n("cc_permissions").format(permissions=", ".join(self.permissions))
        # )

        # Project Info
        if (
            self.config.get("project_id", None) is not None
            and self.config["project_id"] != 0
        ):
            info_msg_lines.extend(
                [
                    self.i18n("cc_ticket_name").format(
                        ticket_name=self.config.get("ticket_name", self.i18n("not_set"))
                    ),
                    self.i18n("cc_project_id").format(
                        project_id=self.config.get("project_id", self.i18n("not_set"))
                    ),
                    self.i18n("cc_screen_id").format(
                        screen_id=self.config.get("screen_id", self.i18n("not_set"))
                    ),
                    self.i18n("cc_sku_id").format(
                        sku_id=self.config.get("sku_id", self.i18n("not_set"))
                    ),
                    self.i18n("cc_count").format(
                        count=self.config.get("count", self.i18n("not_set"))
                    ),
                    self.i18n("cc_order_type").format(
                        order_type=self.config.get("order_type", self.i18n("not_set"))
                    ),
                ]
            )
            ID_BIND_TYPE = {
                0: self.i18n("id_bind_type_0"),
                1: self.i18n("id_bind_type_1"),
                2: self.i18n("id_bind_type_2"),
            }
            info_msg_lines.append(
                self.i18n("cc_id_bind_type").format(
                    id_bind_type=ID_BIND_TYPE.get(
                        self.config.get("id_bind", -1), self.i18n("unknown")
                    )
                )
            )
            ID_TYPE_NAME = {
                0: self.i18n("id_type_idcard"),
                1: self.i18n("id_type_passport"),
                2: self.i18n("id_type_hk_macau"),
                3: self.i18n("id_type_taiwan"),
            }
            if self.config.get("id_bind", -1) == 0:
                info_msg_lines.extend(
                    [
                        self.i18n("cc_buyer").format(
                            buyer=self.config.get("buyer", self.i18n("not_set"))
                        ),
                        self.i18n("cc_tel").format(
                            tel=self.config.get("tel", self.i18n("not_set"))
                        ),
                    ]
                )
            elif self.config.get("id_bind", -1) == 1 or self.config["id_bind"] == 2:
                if len(self.config.get("id_buyer", [])) == 0:
                    info_msg_lines.append(
                        self.i18n("cc_buyer").format(
                            buyer=self.i18n("cc_buyer_not_set")
                        )
                    )
                else:
                    info_msg_lines.append(
                        self.i18n("cc_buyer").format(
                            buyer="\n"
                            + "\n".join(
                                [
                                    f"{buyer['name']} ({ID_TYPE_NAME[buyer['id_type']]}) {buyer['personal_id']} {buyer['tel']}"
                                    for buyer in self.config["id_buyer"]
                                ]
                            )
                        )
                    )
            info_msg_lines.append(
                self.i18n("cc_pay_money").format(
                    pay_money=self.config.get("pay_money", self.i18n("not_set"))
                )
            )
            info_msg_lines.append(
                self.i18n("cc_start_time").format(
                    start_time=time.strftime(
                        "%m-%d %H:%M:%S",
                        time.localtime(self.config.get("sale_start_time", 0)),
                    )
                )
            )
            info_msg_lines.append(
                self.i18n("cc_is_changfan").format(
                    is_changfan=self.config.get("is_changfan", False)
                )
            )
            if self.config["is_changfan"]:
                info_msg_lines.append(
                    self.i18n("cc_changfan_id").format(
                        changfan_id=self.config["linkgood_id"]
                    )
                )
        info_msg_lines.append(
            self.i18n("cc_order_interval").format(
                order_interval=self.config.get("order_interval", 0.3)
            )
        )

        # Push Config Info
        if "push_config" in self.config:
            info_msg_lines.append(
                self.i18n("cc_push_config").format(
                    push_config=", ".join(self.config["push_config"]["push_actions"])
                )
            )

        # Return the info message
        return "\n".join(info_msg_lines)

    def calculate_pay_money(self):
        # TODO: Calculate pay money according to the sku_id and count, and return the pay money.
        return self.config["pay_money"] * self.config["count"]
