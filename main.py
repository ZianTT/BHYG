# Copyright (c) 2023 ZianTT
# bilibili-hyg is licensed under Mulan PubL v2.
# You can use this software according to the terms and conditions of the Mulan PubL v2.
# You may obtain a copy of Mulan PubL v2 at:
#          http://license.coscl.org.cn/MulanPubL-2.0
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PubL v2 for more details.

import os
from api import BilibiliHyg

if __name__ == "__main__":
    # 判断是否存在config.txt文件
    if not os.path.exists("config.txt"):
        bilibili_hyg = BilibiliHyg()
    else:
        with open("config.txt", "r", encoding="utf-8") as f:
            config = f.read()
        if config:
            config = config.split("\n")
            config = [i.split("=") for i in config]
            # 将第一个等号前的内容作为key，第一个等号后的全部内容作为value
            config = {i[0]: "=".join(i[1:]) for i in config}
            bilibili_hyg = BilibiliHyg(**config)
        else:
            bilibili_hyg = BilibiliHyg()
    bilibili_hyg.run()
