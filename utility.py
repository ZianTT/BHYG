import inquirer
import requests
from loguru import logger

def utility(config):
    def add_buyer(headers):
        # buyer = inquirer.prompt([
        #     inquirer.Text("name", message="请输入购票人姓名"),
        #     inquirer.Text("personal_id", message="请输入购票人身份证号码"),
        #     inquirer.List("id_type", message="请选择证件类型", choices=["0. 身份证", "1. 护照", "2. 港澳居民往来内地通行证", "3. 台湾居民往来大陆通行证"], default="身份证"),
        #     inquirer.Text("tel", message="请输入购票人手机号码"),
        # ])
        name = input("请输入购票人姓名：")
        id_type = inquirer.prompt([inquirer.List("id_type", message="请选择证件类型", choices=["0. 身份证", "1. 护照", "2. 港澳居民往来内地通行证", "3. 台湾居民往来大陆通行证"], default="身份证"),
            inquirer.Text("tel", message="请输入购票人手机号码"),
        ])
        personal_id = input("请输入购票人身份证号码：")
        tel = input("请输入购票人手机号码：")
        data = {
            "name": name,
            "tel": tel,
            "id_type": id_type["id_type"].split(".")[0],
            "personal_id": personal_id,
            "is_default": "0",
            "src": "ticket"
        }
        logger.debug(data)
        response = requests.post("https://show.bilibili.com/api/ticket/buyer/create", headers=headers, data=data)
        if response.json()["errno"] == 0:
            logger.info("添加成功")
        else:
            logger.error(f"{response.json()['errno']}: {response.json()['msg']}")
            return add_buyer(headers)

    headers = {
        "Cookie": config["cookie"],
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BHYG/0.7.2",
        "Referer": "https://show.bilibili.com"
    }
    select = inquirer.prompt([
        inquirer.List(
            "select",
            message="请选择您要使用的实用工具",
            choices=["添加购票人"],
        )])
    if select["select"] == "添加购票人":
        add_buyer(headers)
    else:
        logger.error("暂不支持此功能")
        return utility()

if __name__ == "__main__":
    import os
    config = {}
    if os.path.exists("login-info"):
        with open("login-info", "r", encoding="utf-8") as f:
            config["cookie"] = f.read()
    else:
        config["cookie"] = interactive_login()
        with open("login-info", "w", encoding="utf-8") as f:
            f.write(config["cookie"])
    utility(config)