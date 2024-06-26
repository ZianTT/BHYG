import json
import time

import requests

import bili_ticket_gt_python
import loguru

# REF: https://github.com/mikumifa/biliTickerBuy
# REF: https://github.com/Amorter/biliTicker_gt
# LICENSE: GPL-3.0

class Validator():
    def __init__(self):
        self.click = bili_ticket_gt_python.ClickPy()
        pass

    def validate(self, gt, challenge) -> str:
        try:
            validate = self.click.simple_match_retry(gt, challenge)
            return validate
        except Exception as e:
            return ""

def run(gt, challenge, token):
    try:
        validator = Validator()
        validate_string = validator.validate(gt, challenge)
        data = {
                    "success": True,
                    "challenge": challenge,
                    "validate": validate_string,
                    "seccode": validate_string,
            }
            
        return data
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    captcha = requests.get(
        "https://passport.bilibili.com/x/passport-login/captcha", headers={
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/618.1.15.10.15 (KHTML, like Gecko) Mobile/21F90 BiliApp/77900100 os/ios model/iPhone 15 mobi_app/iphone build/77900100 osVer/17.5.1 network/2 channel/AppStore c_locale/zh-Hans_CN s_locale/zh-Hans_CH disable_rcmd/0"
    }
    ).json()
    gt = captcha["data"]["geetest"]["gt"]
    challenge = captcha["data"]["geetest"]["challenge"]
    token = captcha["data"]["token"]
    validator = Validator()
    validate = validator.validate(gt, challenge)
    print(validate)
