# -*- coding: UTF-8 -*-
# Contains functions to display the webpage

import json
import socket

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse


def getPort():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 绑定到本地主机上随机的端口号
    sock.bind(("localhost", 0))
    # 获取绑定后的端口号
    _, port = sock.getsockname()
    # 关闭socket
    sock.close()
    return port


port = getPort()
# NOTE: refactored code, load html instead of hard coding it


def load_template(port):
    template = """

<html>
<head>
    <script src="https://static.geetest.com/static/js/gt.0.4.9.js"></script>
</head>
<body>
   <p>必要时，这里会出现验证码</p> 
    <script>
        function showCaptcha(gt, challenge) {
            initGeetest({
                // 以下配置参数来自服务端 SDK
                product: 'bind',
                gt: gt,
                challenge: challenge,
                offline: false,
                new_captcha: true,
                hideClose:  true,
            }, function (captchaObj) {
                    // 这里可以调用验证实例 captchaObj 的实例方法
                    captchaObj.onReady(function(){
                    //验证码ready之后才能调用verify方法显示验证码
                        captchaObj.verify();
                    });
                    captchaObj.onSuccess(function () {
                        var result = captchaObj.getValidate();
                        data = {
                            success: true,
                            challenge: result.geetest_challenge,
                            validate: result.geetest_validate,
                            seccode: result.geetest_seccode,
                        };
                        fetch("http://127.0.0.1:{{port}}/api?data="+JSON.stringify(data))
                        captchaObj.destroy();
                    });
                    captchaObj.onError(function () {
                        data = {
                            success: false
                        };
                        fetch("http://127.0.0.1:{{port}}/api?data="+JSON.stringify(data))
                        captchaObj.destroy();
                    });
                    captchaObj.onClose(function () {
                        data = {
                            success: false
                        };
                        fetch("http://127.0.0.1:{{port}}/api?data="+JSON.stringify(data))
                        captchaObj.destroy();
                    });
                });
            };
        // 每隔一秒向服务端发送get请求并查看返回值
        setInterval(function() {
            fetch("http://127.0.0.1:{{port}}/api")
            .then(response => response.json())
            .then(data => {
                if (data.type === 'geetest') {
                    showCaptcha(data.data.gt, data.data.challenge)
                }
            });
        }, 1000);

    </script>
</body>
</html>
"""
    return template.replace("{{port}}", str(port))


html = load_template(port)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def main_page():
    # 返回html
    return html


@app.get("/api")
def get(data: str | None = None):
    if data:
        with open("data/tos", "w+") as f:
            f.write(data)
        return "OK"
    with open("data/toc", "a+") as f:
        f.seek(0, 0)
        data = f.read()
        if data == "":
            return {}
        else:
            f.truncate(0)
            return json.loads(data)


def run_web(app, port):
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="critical")
