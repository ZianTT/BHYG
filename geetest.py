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
            (_, _) = self.click.get_c_s(gt, challenge)
            _type = self.click.get_type(gt, challenge)
            if _type != "click":
                raise Exception("验证码类型错误")
            (c, s, args) = self.click.get_new_c_s_args(gt, challenge)
            before_calculate_key = time.time()
            key = self.click.calculate_key(args)
            w = self.click.generate_w(key, gt, challenge, str(c), s, "abcdefghijklmnop")
            w_use_time = time.time() - before_calculate_key
            loguru.logger.info(f"w生成时间：{w_use_time}")
            if w_use_time < 3:
                time.sleep(3 - w_use_time)
            (msg, validate) = self.click.verify(gt, challenge, w)
            while validate is None:
                (msg, validate) = self.click.verify(gt, challenge, w)
            loguru.logger.info(f"msg: {msg} ; validate: {validate}")
            return validate
        except Exception as e:
            return ""

def run(gt, challenge, token):
    try:
        validator = Validator()
        validate_string = validator.validate(gt, challenge)
        if validate_string != "" and validate_string != None:
            with open("data/tos", "w+") as f:
                data = {
                    "success": True,
                    "challenge": challenge,
                    "validate": validate_string,
                    "seccode": validate_string,
                }
                f.write(json.dumps(data))
            return True
    except Exception as e:
        print(f"Error: {e}")