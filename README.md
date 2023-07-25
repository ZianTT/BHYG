# bilibili-hyg

bilibili 会员购 抢票脚本

PS: 在branch dev 是有新的开发版本，各位大佬感兴趣可以先做个测试，有bug可以发issue提出，感谢各位大佬

恳请各位大佬点个免费的星星⭐️支持一下鸭

本脚本不同于其他脚本，直接调用api，存在一定风控风险，脚本提供者不为您的行为负责。

本脚本仅供学习交流，请在24小时内停止运行并删除本脚本。

**常见问题请参考**[**FAQ Wiki**](https://github.com/ZianTT/bilibili-hyg/wiki/FAQ)

[关于这个项目的初衷](https://github.com/ZianTT/bilibili-hyg/wiki/%E5%85%B3%E4%BA%8E%E8%BF%99%E4%B8%AA%E9%A1%B9%E7%9B%AE)

PS：针对GeeTest验证码我也没有什么好的解决方案，如果有xd有GeeTest的能用的现成轮子欢迎推荐给我吖

## 使用教程

前往[Release](https://github.com/ZianTT/bilibili-hyg/releases)下载对应文件，双击打开

打开login.exe，扫描二维码登录获得到cookie

项目id则为活动详情页url中id的参数，一般为7开头的数字，如BW2023为73710

接下来根据提示选择场次，购票人（购买单场次多张票可多选购票人，格式：0,1）

触发风控时，请访问给出的链接人工验证，完成验证后按下回车继续

若抢票成功，可在任何一端访问订单页支付，防止放票

如有侵权请联系删除

## 参数公示

售票状态及票数刷新间隔：(0.3+0.1\[请求延时\])秒

下单token刷新：不定时，约 (0.3+0.1)\*800/2=120秒

下订单刷新：不定时，约0.1s\[请求延时\]秒

有票后下订单总次数：20次
