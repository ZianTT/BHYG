import httpx
from loguru import logger


def push_gotify(url, token, message, jump_url):
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token}
    data = {
        "message": message,
        "extras": {
            "client::notification": {
                "click": {"url": jump_url},
            },
            "android::action": {"onReceive": {"intentUrl": jump_url}},
        },
    }
    try:
        with httpx.Client(base_url=url, follow_redirects=True) as client:
            response = client.post("/message", headers=headers, json=data)
            response.raise_for_status()
            logger.debug(response.json())
            return True
    except httpx.HTTPStatusError:
        return False
    except Exception as e:
        logger.debug(e)
        return False


def ob11_push(url, token, send_type, send_target, message, image):
    headers = {"Content-Type": "application/json"}
    if token is not None and token != "":
        headers["Authorization"] = "Bearer " + token
    if send_type not in ["private", "group"]:
        return False
    data = {
        f"{'user' if send_type == 'private' else 'group'}_id": send_target,
        "message": [
            {"type": "text", "data": {"text": message}},
            {
                "type": "image",
                "data": {
                    "file": f"base64://{image}",
                },
            },
        ],
    }
    try:
        with httpx.Client(base_url=url, follow_redirects=True) as client:
            response = client.post(f"/send_{send_type}_msg", headers=headers, json=data)
            response.raise_for_status()
            logger.debug(response.json())
            return True if response.json()["retcode"] == 0 else False
    except httpx.HTTPStatusError:
        return False
    except Exception as e:
        logger.debug(e)
        return False

def milky_push(url, token, send_type, send_target, message, image):
    headers = {"Content-Type": "application/json"}
    if token is not None and token != "":
        headers["Authorization"] = "Bearer " + token
    if send_type not in ["private", "group"]:
        return False
    data = {
        f"{'user' if send_type == 'private' else 'group'}_id": send_target,
        "message": [
            {"type": "text", "data": {"text": message}}
        ],
    }
    try:
        with httpx.Client(base_url=url, follow_redirects=True) as client:
            response = client.post(f"/api/send_{send_type}_message", headers=headers, json=data)
            response.raise_for_status()
            logger.debug(response.json())
            return True if response.json()["retcode"] == 0 else False
    except httpx.HTTPStatusError:
        logger.debug(response.text)
        return False
    except Exception as e:
        logger.debug(e)
        return False

def push_bark(url, key, message, jump_url, enhanced=False):
    headers = {"Content-Type": "application/json"}
    data = {
        "body": message,
        "title": "【BHYG】锁票成功，尽快支付",
        "device_key": key,
        "url": jump_url,
    }
    if enhanced:
        data["level"] = "critical"
        data["call"] = "1"
        data["volume"] = 10
    try:
        with httpx.Client(base_url=url, follow_redirects=True) as client:
            response = client.post("/push", headers=headers, json=data)
            logger.debug(response.json())
            return True
    except httpx.HTTPStatusError:
        return False
    except Exception as e:
        logger.debug(e)
        return False


def push_ntfy(url, key, title, message, jump_url):
    headers = {"Content-Type": "application/json"}
    data = {
        "topic": key,
        "message": title,
        "title": message,
        "tags": ["tada", "loudspeaker"],
        "priority": 5,
        "click": jump_url,
        "actions": [{"action": "view", "label": "付款", "url": jump_url}],
    }
    try:
        with httpx.Client(base_url=url, follow_redirects=True) as client:
            response = client.post("/", headers=headers, json=data)
            logger.debug(response.json())
            return True
    except httpx.HTTPStatusError:
        return False
    except Exception as e:
        logger.debug(e)
        return False


def desktop_notify(title, message, need_sound, sound_path):
    try:
        from notifypy import Notify

        notification = Notify()
        notification.title = title
        notification.message = message
        notification.send()
        if need_sound:
            try:
                from playsound3 import playsound

                logger.debug(f"playing sound...")
                playsound(sound=sound_path, block=False)
            except:
                logger.warning("playsound failed")
        return True
    except BaseException as e:
        logger.debug(e)
        return False


def push_pushplus(token, message, content):
    headers = {"Content-Type": "application/json"}
    data = {
        "token": token,
        "title": message,
        "content": content,
    }
    try:
        response = httpx.post(
            "http://www.pushplus.plus/send", headers=headers, json=data
        )
        response.raise_for_status()
        logger.debug(response.json())
        return True if response.json()["code"] == 200 else False
    except httpx.HTTPStatusError:
        return False
    except Exception as e:
        logger.debug(e)
        return False


def push_server_chan(send_key: str, message, content):
    import re

    if send_key.startswith("sctp"):
        match = re.match(r"sctp(\d+)t", send_key)
        if match:
            num = match.group(1)
            url = f"https://{num}.push.ft07.com/send/{send_key}.send"
        else:
            raise ValueError("Invalid sendkey format for sctp")
    else:
        url = f"https://sctapi.ftqq.com/{send_key}.send"
    params = {
        "title": message,
        "desp": content,
    }
    try:
        response = httpx.get(url, params=params)
        response.raise_for_status()
        logger.debug(response.json())
        return True if response.json()["code"] == 0 else False
    except httpx.HTTPStatusError:
        return False
    except Exception as e:
        logger.debug(e)
        return False


def do_push(
    push_config,
    order_id,
    ticket_name,
    buyer_name,
    username,
    code_url="iVBORw0KGgoAAAANSUhEUgAAATYAAAE2AQAAAADDx4MEAAABnUlEQVR4nO2aTY7DIAyFHwSpS3IjevRylB6gUrIcKZFHJs5MO3KlbqbQ4LcgCf0kjJB/gDrCK1r9SxhgnC7jdBmnyzhdxukyTlenXHYi5LF0rHvH2IR93XGRWAuQrs65M4DSQZdG7OuOW8UX8jjQ5iTsM+3Y1yuXaMGPV7xx3Cfyz37oh1tdnXFVdcsNRDSVKBWAxG+JiNqxrzNuLsVU4My+cBIBtvLq3Ih9vXCgv5oGKq7xoKX1efiDcJCyNi6QepfXg8tfyexSCLc+D38QDr/bDLrsSYSkkZWx9agSr8AOIX1TCVrsLhavasUrcJFVSisq4UsaW493ckGe84kc4s1RHocF6XoiYA6fMw9/EC5sj0QAbzb2DUf8coR4Cx8zD38QDo/HhluUKrJ6t2r+oO18V1L5xD5Tiixbjyr5A2sA4k0+MieR0vzXuN44VXcpe9fqqBwqJipvnzEPf1QujwPJqdUcYPeD1fPHJo5U8e6z9Xn4o57v5rFcnQcQ8SZErtOr29cL5+z/iaqM02WcLuN0GafLOF3G6Xq13v0Guvwt2WnbzoMAAAAASUVORK5CYII=",
):
    success = True
    for push_type in push_config["push_actions"]:
        if push_type == "gotify":
            if not push_gotify(
                push_config["gotify"]["server"],
                push_config["gotify"]["token"],
                f"【BHYG】锁票成功，尽快支付，点击跳转\n票名: {ticket_name}\n购票人: {buyer_name}\n用户: {username}\n订单ID: {order_id}",
                f"bilibili://mall/web?url=https://mall.bilibili.com/neul-next/ticket/orderDetail.html?order_id={order_id}",
            ):
                success = False
        elif push_type == "ob11":
            if not ob11_push(
                push_config["ob11"]["server"],
                push_config["ob11"]["token"],
                push_config["ob11"]["send_type"],
                push_config["ob11"]["send_target"],
                f"【BHYG】锁票成功，尽快支付。\n票名: {ticket_name}\n购票人: {buyer_name}\n用户: {username}\n订单ID: {order_id}\nhttps://mall.bilibili.com/neul-next/ticket/orderDetail.html?order_id={order_id}\n可扫描下方二维码支付",
                code_url,
            ):
                success = False
        elif push_type == "milky":
            if not milky_push(
                push_config["milky"]["server"],
                push_config["milky"]["token"],
                push_config["milky"]["send_type"],
                push_config["milky"]["send_target"],
                f"【BHYG】锁票成功，尽快支付。\n票名: {ticket_name}\n购票人: {buyer_name}\n用户: {username}\n订单ID: {order_id}\nhttps://mall.bilibili.com/neul-next/ticket/orderDetail.html?order_id={order_id}",
                code_url,
            ):
                success = False
        elif push_type == "bark":
            if not push_bark(
                push_config["bark"]["server"],
                push_config["bark"]["key"],
                f"【BHYG】锁票成功，尽快支付，点击跳转\n票名: {ticket_name}\n购票人: {buyer_name}\n用户: {username}\n订单ID: {order_id}",
                f"bilibili://browser?url=https://mall.bilibili.com/neul-next/ticket/orderDetail.html?order_id={order_id}",
                push_config["bark"]["enhanced"],
            ):
                success = False
        elif push_type == "desktop_notify":
            if len(ticket_name) > 45:
                ticket_name = ticket_name[:12] + "..." + ticket_name[-30:]
            if not desktop_notify(
                f"【BHYG】锁票成功，尽快支付。",
                f"票名: {ticket_name}\n购票人: {buyer_name} 用户: {username}\n订单ID: {order_id}",
                push_config["desktop_notify"]["need_sound"],
                push_config["desktop_notify"]["sound_path"],
            ):
                success = False
        elif push_type == "pushplus":
            if not push_pushplus(
                push_config["pushplus"]["token"],
                f"【BHYG】锁票成功，尽快支付。",
                f"票名: {ticket_name}\n购票人: {buyer_name}\n用户: {username}\n订单ID：{order_id}\nhttps://mall.bilibili.com/neul-next/ticket/orderDetail.html?order_id={order_id}",
            ):
                success = False
        elif push_type == "server_chan":
            if not push_server_chan(
                push_config["server_chan"]["send_key"],
                f"【BHYG】锁票成功，尽快支付。",
                f"票名: {ticket_name}\n购票人: {buyer_name}\n用户: {username}\n订单ID：{order_id}\nhttps://mall.bilibili.com/neul-next/ticket/orderDetail.html?order_id={order_id}",
            ):
                success = False
        elif push_type == "ntfy":
            if not push_ntfy(
                push_config["ntfy"]["server"],
                push_config["ntfy"]["topic"],
                f"【BHYG】锁票成功，尽快支付。",
                f"票名: {ticket_name}\n购票人: {buyer_name}\n用户: {username}\n订单ID: {order_id}",
                f"bilibili://browser?url=https://mall.bilibili.com/neul-next/ticket/orderDetail.html?order_id={order_id}",
            ):
                success = False
        elif push_type == "run_command":
            import subprocess

            try:
                command = push_config["run_command"]["command"]
                command = command.replace("ORDER_ID", order_id)
                command = command.replace("TICKET_NAME", ticket_name)
                command = command.replace("BUYER_NAME", buyer_name)
                command = command.replace("USERNAME", username)
                logger.debug(f"run command: {command}")
                subprocess.run(command)
            except Exception as e:
                logger.debug(e)
                success = False

    return success
