# BiliHYG

一个使用API接口来在会员购抢票的校本


## 使用须知

本脚本直接调用api，存在一定风控风险，包括但不限于暂时屏蔽请求、封禁账号，**脚本提供者不为您的行为负责**。

本脚本仅供学习交流，请在24小时内停止运行并删除本脚本。

常见问题可以参考原仓库的[FAQ Wiki](https://github.com/ZianTT/bilibili-hyg/wiki/FAQ)

如有侵权请联系删除


## 使用教程

前往Release下载对应文件，双击打开，按照提示操作即可

如果使用源码，请打开`main.py``


## TODO

 -[ ] GeeTest: 针对GeeTest验证码我也没有什么好的解决方案，如果有GeeTest的能用的现成轮子欢迎推荐


## 有关参数

这里列出的参数你可以下载源码在各个文件的头部修改

 |                **参数**                 |                 **意义**                  |                                                       **默认值 **                                                       |
 | :-------------------------------------: | :---------------------------------------: | :---------------------------------------------------------------------------------------------------------------------: |
 |    **REST_BETWEEN_STARTING_THREADS**    |            启动多线程的间隔(s)            |                                                            1                                                            |
 |        **REST_IN_GETTING_TOKEN**        |   获取OrderToken时的间歇，各线程相同(s)   |                                                           .5                                                            |
 |         **REST_WHILE_RUNNING**          | 获取到OrderToken后发包间歇，各线程相同(s) |                                                           .3                                                            |
 |           **CONNECT_TIMEOUT**           |      默认连接超时时间，各线程相同(s)      |                                                          1.03                                                           |
 |            **READ_TIMEOUT**             |      默认读取超时时间，各线程相同(s)      |                                                          1.03                                                           |
 | **CONNECT_TIMEOUT_WHEN_CREATING_ORDER** |   创建订单时连接超时时间，各线程相同(s)   |                                                          5.03                                                           |
 |  **READ_TIMEOUT_WHEN_CREATING_ORDER**   |   创建订单时读取超时时间，各线程相同(s)   |                                                          5.03                                                           |
 |             **TOKEN_LIFE**              |    一个Token可以使用多少次，各线程相同    |                                                           400                                                           |
 |    **RETRY_TIMES_WHEN_STATUS_IS_OK**    | 当抢票开始时，连续发包多少次，各线程相同  |                                                           20                                                            |
 |              **UA_OF_PC1**              |                 电脑UA头1                 | 'Mozilla/5.0(WindowsNT10.0;Win64;x64)AppleWebKit/537.36(KHTML,likeGecko)Chrome/108.0.0.0Safari/537.36Edg/108.0.1462.42' |
 |              **UA_OF_PC2**              |                 电脑UA头2                 |                              'Mozilla/5.0(Macintosh;IntelMacOSX10_15_7)AppleWebKit/537.36'                              |
 |            **UA_OF_MOBILE**             |                 手机UA头1                 |        'Mozilla/5.0(Linux;U;Android8.1.0;zh-cn;BLA-AL00Build/HUAWEIBLA-AL00)AppleWebKit/537.36(KHTML,likeGecko)'        |

