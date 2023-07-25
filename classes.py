"""
Copyright (c) 2023 bilibaiWater
BiliHYG is licensed under Mulan PubL v2.
You can use this software according to the terms and conditions of the Mulan PubL v2.
You may obtain a copy of Mulan PubL v2 at:
         http://license.coscl.org.cn/MulanPubL-2.0
THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
See the Mulan PubL v2 for more details.
"""

import datetime
import json
import os
import time
import webbrowser
import requests
import requests.utils

from utils import get_logger_, get_ms_timestamp

logger = get_logger_('class.py')

REST_IN_GETTING_TOKEN = .5
REST_WHILE_RUNNING = .3

CONNECT_TIMEOUT = 1.03
READ_TIMEOUT = 1.03
CONNECT_TIMEOUT_WHEN_CREATING_ORDER = 5.03
READ_TIMEOUT_WHEN_CREATING_ORDER = 5.03

TOKEN_LIFE = 400
RETRY_TIMES_WHEN_STATUS_IS_OK = 20

UA_OF_PC1 = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.42'
UA_OF_PC2 = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
UA_OF_MOBILE = 'Mozilla/5.0 (Linux; U; Android 8.1.0; zh-cn; BLA-AL00 Build/HUAWEIBLA-AL00) AppleWebKit/537.36 (KHTML, like Gecko)'


class BiliException(Exception):
    pass


class BiliObjects:
    pass


class BiliLogin(BiliObjects):
    def __init__(self) -> None:
        print('\n===============STEP 0===============')

    def _get_qrcode_url(self) -> str:
        qrcode_url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
        headers = {
            'User-Agent': UA_OF_PC1
        }

        response = self.session.get(qrcode_url, headers=headers).json()
        if response['code'] == 0:
            url = response['data']['url']
            key = response['data']['qrcode_key']
            logger.debug('QRCODE url: %s' % url)
            logger.debug('QRCODE key: %s' % key)

            return url, key
        else:
            logger.error('get QRCODE url failed. Response: %s' % response)
            raise BiliException(
                'get QRCODE url failed. Response: %s' % response)

    def _do_login(self):

        import qrcode
        self.session = requests.session()
        self._login_qrcode_url, self._login_qrcode_key = self._get_qrcode_url()

        qrcode_obj = qrcode.QRCode()
        qrcode_obj.add_data(self._login_qrcode_url)
        qrcode_obj.print_ascii(invert=True)
        logger.info('login QRCODE showed in console.')
        qrcode_obj.make_image().save('login.png')
        os.system('start login.png')
        logger.info('login QRCODE png file showed.')

        response_url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key=%s' % self._login_qrcode_key
        while True:
            response = self.session.get(response_url).json()
            data = response['data']

            if data['code'] == 0:
                print(
                    '请使用bilibili手机客户端扫码登录(任何一个二维码都可以)。\t\t[已确认]\t可以关闭图片查看器了.')
                self._save_cookie()
                self._test_cookie()
                break

            elif data['code'] == 86101:
                print('请使用bilibili手机客户端扫码登录(任何一个二维码都可以)。\t\t[未扫码]', end='\r')

            elif data['code'] == 86090:
                print('请使用bilibili手机客户端扫码登录(任何一个二维码都可以)。\t\t[未确认]', end='\r')

            else:
                code = data['code']
                logger.error(f'unknown code: {code}. response: {data}')
                raise BiliException(f'unknown code: {code}. response: {data}')

            time.sleep(1)

    def _save_cookie(self):
        cookies: dict = requests.utils.dict_from_cookiejar(
            self.session.cookies)
        lst = [f'{i[0]}={i[1]}' for i in cookies.items()]
        self._cookie_str = ';'.join(lst)
        logger.info(f'cookie: {self._cookie_str}')

    def _test_cookie(self, cookie: str | None = None):
        url = 'https://api.bilibili.com/x/web-interface/nav'
        headers = {
            'user-agent': UA_OF_PC1,
            'cookie': cookie if cookie is not None else self._cookie_str,
        }

        logger.info('testing cookie...')
        response = requests.get(url, headers=headers).json()
        if response['data']['isLogin']:
            username = response['data']['uname']
            logger.info(f'logged in successfully. username: {username}')
            print(f'用户【{username}】登陆成功.')

            return True
        else:
            logger.error(f'failed in logging in. response: {response}')
            raise BiliException(f'Login Failed. Test response: {response}')

    @classmethod
    def get_cookie(cls):
        login_obj = cls()
        if hasattr(login_obj, '_cookie_str'):
            return login_obj._cookie_str
        else:
            login_obj._do_login()
            return login_obj._cookie_str

    @classmethod
    def test_or_get_cookie(cls, cookie: str):
        login_obj = cls()
        if login_obj._test_cookie(cookie=cookie):
            return cookie
        return login_obj._do_login()


class BiliTickets(BiliObjects):
    def __init__(self, project_id: int | None = None) -> None:
        self._user_cookie = BiliLogin.get_cookie()
        self._headers = {
            'Host': 'show.bilibili.com',
            'Connection': 'keep-alive',
            'Cookie': self._user_cookie,
            'Accept': '*/*',
            'Origin': 'https://show.bilibili.com',
            'User-Agent': UA_OF_PC2
        }
        self._risk = False

        # ticket ID
        if project_id is None:
            self._project_id = self._get_project_id()
        else:
            self._project_id = project_id
        logger.info(f'show ID: {self._project_id}')
        self._get_ticket_info()

        # buyer info
        self._choose_buyer_info()

    def _get_project_id(self):
        print('\n===============STEP 1===============')
        input_ = input('请输入项目id或者粘贴分享链接: \t\t>>>\t')
        logger.debug('user input: %s' % input_)

        try:
            show_id = int(input_)
            return show_id
        except ValueError:
            import re
            pattern = re.compile('(id=[1-9][0-9]*)')
            result = pattern.findall(input_)[0]
            show_id = result[3:]
            return int(show_id)

    def _get_ticket_info(self):
        url = f'https://show.bilibili.com/api/ticket/project/get?version=134&id={self._project_id}'
        response: dict = requests.get(url, headers=self._headers).json()
        self._project_name = response['data']['name']
        logger.debug(f'ticket info got. Detail: {response}')

        # 暂无判断方式：没找到flag
        self._need_real_name = True if ('实名' in str(response)) else False
        if not self._need_real_name:
            logger.info(
                f'looks like this project dosen\'t need a real name...')

        screens = response['data']['screen_list']
        print('\n===============STEP 2===============')
        for i in range(len(screens)):
            name = screens[i]['name']
            print(f'[{i}] | {name}')
        screen = int(input('请输入场次序号[请注意序号从0开始]:\t\t>>>\t'))
        self._screen_index = screen  # 先存起来
        screen_id = screens[screen]['id']
        screen_str = screens[screen]['name']
        logger.info(f'screen chose: {screen_id}, {screen_str}')

        tickets = screens[screen]['ticket_list']
        print('\n===============STEP 3===============')
        for i in range(len(tickets)):
            desc = tickets[i]['desc']
            money = tickets[i]['price']/100
            print(f'[{i}] | {desc}(RMB {money}元)')
        sku = int(input('请输入票档序号[请注意序号从0开始]:\t\t>>>\t'))
        self._sku_index = sku  # 先存起来
        sku_id = tickets[sku]['id']
        pay_money = tickets[sku]['price']
        sku_str = tickets[sku]['desc']
        logger.info(f'sku chose: {sku_id}, {sku_str}, pay_money: {pay_money}')

        self._screen_id = screen_id
        self._sku_id = sku_id
        self._pay_money = pay_money
        self._ticket_info_str = f'{screen_str}, {sku_str}'

    def _choose_buyer_info(self):
        print('\n===============STEP 4===============')
        if not self._need_real_name:
            input_ = input('本票似乎不需要实名购买。请再次确认是否需要实名购买。'
                           '需要输入1, 不需要输入0. \t\t>>>\t')
            if not int(input_):
                self._need_real_name = False
                logger.info('user stopped this function. No buyer info will be posted. '
                            'Instead, user need to leave contant info')
                self._get_contant_info()
                return
            logger.info('user chose to continue.')

        self._need_real_name = True
        url = 'https://show.bilibili.com/api/ticket/buyer/list'
        response = requests.get(url, headers=self._headers)
        all_buyers_info = response.json()['data']['list']
        logger.debug(f'buyer info got. Detail: {all_buyers_info}')

        if len(all_buyers_info) == 0:
            logger.info('buyers not found. Exit. ')
            raise BiliException(
                f'Buyers info not found. please add buyer\'s info on APP. ')

        input_ = ''
        msg = ''
        marks = [False for _ in range(len(all_buyers_info))]
        while True:
            print('\n====================================')
            for i in range(len(all_buyers_info)):
                name = all_buyers_info[i]['name']
                personal_id = all_buyers_info[i]['personal_id']
                tel = all_buyers_info[i]['tel']
                mark = 'o' if marks[i] else ' '
                print(f'[{mark}] [{i}] {name}\t{personal_id}\t{tel}')
            print('请选择购买人. [+X]添加序号为X, [-X]去除序号X, [ALL]全选, [DONE]完成.')
            print(f'{msg} [请注意序号从0开始]')
            input_ = input('[o]已选[ ]未选, 最多选中4个\t\t>>>\t').lower()
            logger.debug(f'Inputed: {input_}')
            if input_ == 'all':
                if len(all_buyers_info) >= 4:
                    msg = '达咩!最多选中4人!'
                    logger.debug('too many buyers!')
                else:
                    marks = [True for _ in range(len(all_buyers_info))]
                    logger.debug('choose all successfully')
                    break
            elif input_ == 'done':
                break
            elif input_.startswith('+'):
                index = int(input_[1:])
                marks[index] = True
                name = all_buyers_info[index]['name']
                msg = f'选中{name}'
                logger.debug(f'chose {name}')
            elif input_.startswith('-'):
                index = int(input_[1:])
                marks[index] = False
                name = all_buyers_info[index]['name']
                msg = f'取消选中{name}'
                logger.debug(f'un-chose {name}')
            else:
                msg = '输入有误'

        chose_buyers = []
        buyers_names = []
        for i in range(len(all_buyers_info)):
            if marks[i]:
                chose_buyers.append(all_buyers_info[i])
                buyers_names.append(all_buyers_info[i]['name'])

        self._buyers_str = '【实名展/{}人】{}'.format(
            len(buyers_names), ', '.join(buyers_names))
        self._buyers = json.dumps(chose_buyers)
        self._tickets_count = len(chose_buyers)
        logger.info(
            f'buyers are: {self._buyers_str}, {self._tickets_count} in total')

    def _get_contant_info(self):
        print('注意: 非实名展演有【必填】的联系信息. 请填写. ')
        self._not_real_name_buyer = input('请输入姓名\t\t>>>\t')
        self._not_real_name_tel = input('请输入手机号\t\t>>>\t')
        self._tickets_count = int(input('请输入购买张数\t\t>>>\t'))

        self._contant_info = f'【非实名展】联系人: {self._not_real_name_buyer}, 电话: {self._not_real_name_tel}'
        logger.info(f'{self._contant_info}, count: {self._tickets_count}')

    # ==========================================================================

    def run(self, thread_name: str):
        def __get_tickets_status_code() -> int:
            '''retuen the status code of ticket'''

            ticket_url = f'https://show.bilibili.com/api/ticket/project/get?version=134&id={self._project_id}'
            try:
                # TODO: get?
                # NOTE: here is CONNECT TIMEOUT!!!!!
                # readtimeout
                response = requests.get(ticket_url, headers=self._headers, timeout=(
                    CONNECT_TIMEOUT, READ_TIMEOUT))
            except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
                logger.warning(
                    f'connect/read time out!!! params: ({CONNECT_TIMEOUT}, {READ_TIMEOUT}), error: {e}')
                print('连接超时')
                return -1

            try:
                all_screens = response.json()['data']['screen_list']

                screen = all_screens[self._screen_index]
                if screen['id'] != self._screen_id:
                    logger.error(
                        f'screen not found!! response: {response.json()}')
                    print('未找到场次')
                    return -1

                all_skus = screen['ticket_list']

                sku = all_skus[self._sku_index]
                if sku['id'] != self._sku_id:
                    logger.error(
                        f'sku not found!! response: {response.json()}')
                    print('未找到票档')
                    return -1

                logger.debug(f'response: {response.json()}')
                return int(sku['sale_flag_number'])

            except Exception as e:
                logger.warning(f'CAPTCHA? error: {e}')
                return -1

        counter = 0
        status = -1
        self._refresh_token(thread_name)

        while True:
            # pre-check
            if counter >= TOKEN_LIFE:
                self._refresh_token(thread_name)
                counter = 0
                logger.info(
                    f'{thread_name}: touched counter limitation. reset token and counter.')

            if counter % 50 == 0:
                logger.info(
                    f'{thread_name}: init/has ran 50 times. testing risk...')
                self._risk = self._test_risk()

            if self._risk:
                exit()

            # get code and run!
            status = __get_tickets_status_code()
            logger.debug(f'{thread_name}: Status code: {status}')

            if status == -1:
                continue
            elif status == 2:
                for _ in range(RETRY_TIMES_WHEN_STATUS_IS_OK):
                    self._create_order(thread_name)
                    counter += 1
            elif status == 1:
                print(f'{thread_name}: 未开放购票')
            elif status == 4:
                print(f'{thread_name}: 已售罄')
            elif status == 8:
                print(f'{thread_name}: 暂时售罄，即将放票')
            else:
                print(f'{thread_name}: 未知状态: {status}')
                continue

            counter += 1

    def _refresh_token(self, thread_name: str):
        def __requset_prepare_page(token=''):
            url = f'https://show.bilibili.com/api/ticket/order/prepare?project_id={self._project_id}'
            data = {
                'project_id': self._project_id,
                'screen_id': self._screen_id,
                'order_type': '1',
                'count': self._tickets_count,
                'sku_id': self._sku_id,
                'token': token,  # 不需要传入Token也可以拿到返回的Token...
            }
            response = requests.post(
                url, headers=self._headers, data=data).json()
            logger.debug(f'response: {response}')

            if response['errno'] == 100039:
                logger.info('activity has already ended.')
                print(f'{thread_name}: 活动已经结束! ')
                raise BiliException('Activity has already ended!')

            elif response['errno'] != 0:
                msg = response['msg']
                errno = response['errno']
                logger.error(
                    f'msg: {msg}, errno: {errno}, response: {response}')

            return response['data']

        def __get_time_str():
            return datetime.datetime.now().strftime('%H-%M-%S')

        info = __requset_prepare_page()

        while True:
            while (info == {}):
                logger.info('wait... it wasn\'t open to purchase tickets.')
                print(
                    f'{thread_name}: [{ __get_time_str()}]暂未开放购票/无票!', end='\r')
                time.sleep(REST_IN_GETTING_TOKEN)
                info = __requset_prepare_page()

            if info['shield']['open'] == 0:
                order_token = info['token']
                print(f'{thread_name}: Order token GOT! {order_token}')
                logger.info(f'order token GOT! {order_token}')

                self._order_token = order_token
                return

            else:
                # 这里肯定有问题！！！！怎么可能验证完就跑了？肯定有验证后的token来的
                verify_method = info['shield']['verifyMethod']
                verify_url = info['shield']['naUrl']
                logger.warning(
                    f'{thread_name}: CAPTCHA needed! method: {verify_method}, url: {verify_url}')
                print('需要人机验证! 浏览器已经启动... 完成后, 回车继续.')
                logger.debug('ready to open browser...')
                webbrowser.open_new(verify_url)
                logger.debug('browser opened.')
                input('完成验证后, 按回车继续\t\t>>>\t')
                logger.debug('verify ended.')
                # return self._get_token()  # 直接返回自己...额..

    def _create_order(self, thread_name: str):
        url = 'https://show.bilibili.com/api/ticket/order/createV2'

        # set data
        data = {
            'screen_id': self._screen_id,
            'sku_id': self._sku_id,
            'token': self._order_token,
            # 'deviceId': '',  # 浏览器指纹? 是一个在cookie里的[buvid3]的值，但是没找到!
            'project_id': self._project_id,
            'pay_money': int(float(self._pay_money) * int(self._tickets_count)),
            'count': self._tickets_count,
            # 'timestamp': get_ms_timestamp(),
        }

        # if self.riskheader != '':
        #     data['risk_header'] = self.riskheader

        if hasattr(self, '_buyers'):
            data['buyer_info'] = self._buyers
        else:
            data['buyer'] = self._not_real_name_buyer
            data['tel'] = self._not_real_name_tel

        # send req
        try:
            response = requests.post(url, headers=self._headers, data=data, timeout=(
                CONNECT_TIMEOUT_WHEN_CREATING_ORDER, READ_TIMEOUT_WHEN_CREATING_ORDER))
            pass
        except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
            logger.info(f'connected/read time out. error:{e}')
            print(f'{thread_name}: Connect Time Out. Retrying...')
            return False

        if response.status_code == 412:
            logger.critical('CODE: 412. That means [The request was rejected '
                            'because of the bilibili security control policy]!!!!')
            print(f'{thread_name}: status code 412. 请立刻*停止*程序!!')
            msg = (
                '=====================关于状态码412=====================',
                '| 这意味着你触发了哔哩哔哩安全风控策略, 该次访问请求被拒绝.',
                '| 英文原文是: The request was rejected because of the ',
                '| bilibili security control policy.',
                '| 暂无解决方案. 你可以尝试更换IP / 更换账号',
                '| **至少重新登陆!!**',
                '| 再次声明, 账号被封禁和一切意外情况, 软件作者不担负任何责任! ',
                '======================================================',
            )
            for i in msg:
                print(i)
            self._risk = True
            os.remove('bili_tickets.pkl')
            raise BiliException('The request was rejected because of the '
                                'bilibili security control policy')

        result = response.json()
        logger.debug(f'response: {response}')
        # check result
        if result['errno'] == 100001:
            logger.info('前方拥挤, 再试一次吧~')
            print(f'{thread_name}: 拥挤.')
            return False
        elif result['errno'] == 0:
            logger.info(
                'order created successfully. checking if the ticket is fake...')
            pay_token = result['data']['token']
            if (self._check_ticket(pay_token, thread_name)):
                exit()
            else:
                logger.error('fake ticket. continue...')
                return False
        elif result['errno'] == 100009:
            logger.info('no tickets left. Maybe it is Bili\'s problem.')
            print(f'{thread_name}: 无票!')
            return False
        elif result['errno'] == 100051:
            self._order_token = self._refresh_token(thread_name)
            return False
        elif result['errno'] == 100079:
            logger.info('already got ticket(s)!')
            print(f'{thread_name}: 你已经有票了!')
            exit()
        elif result['errno'] == 100048:
            order_id = result['data']['order_id']
            logger.info(f'an order not payed. order_id: {order_id}')
            logger.warning(
                'if u want to get more tickets, u have to pay the exist bill first!')
            print(
                f'{thread_name}: 存在订单未付款, 如果你想继续购票, 那么你需要先在APP中付款! order_id: {order_id}.')
            exit()
        else:
            logger.error(f'unknown error:{result}')
            print(f'{thread_name}: 未知错误: {result}')
            return False

    def _check_ticket(self, pay_token: str, thread_name: str) -> bool:
        url = ('https://show.bilibili.com/api/ticket/order/createstatus?project_id='
               f'{self._project_id}&token={pay_token}&timestamp={get_ms_timestamp()}')
        response = requests.get(url, headers=self._headers).json()

        if response['errno'] == 0:
            import qrcode

            order_id = response['data']['order_id']
            pay_url = response['data']['payParam']['code_url']
            logger.info('order created successfully!!! YESSSSSSSSSSSSSSSSSSS!'
                        f'order_id {order_id}, pay_url {pay_url}')
            print(f'{thread_name}: 成功创建订单!')
            print(f'{thread_name}: 请扫码支付(?如果扫的出来), 或者在会员购-订单中心-待支付中支付. '
                  'Anyway, 你确实抢到票了! 恭喜! ')

            self._risk = True  # 用这个退出其他线程吧 XD

            qr = qrcode.QRCode()
            qr.add_data(pay_url)
            qr.print_ascii(invert=True)
            qr.make_image().save('pay.png')
            os.system('start pay.png')

            return True
        else:
            logger.info('failed. it was fake ticket!')
            return False

    def _test_risk(self) -> bool:
        url = 'https://show.bilibili.com/api/ticket/order/createV2'
        response = requests.get(
            url, headers=self._headers)  # get是405啊?
        logger.debug('Risk Test Status_code: {}'.format(response.status_code))

        if response.status_code == 412:
            return True
        elif response.status_code == 405:
            return False
        else:
            try:
                logger.error(
                    'Unknown Status Code. Response: {}'.format(response.json()))
            except:
                logger.error(
                    'Can\'t encode with JSON. Text: {}'.format(response.text))

            return False  # ..?

    # ==========================================================================

    def save_object(self, filepath: str = 'bili_tickets.pkl'):
        import pickle
        with open(filepath, 'wb') as pkl:
            pickle.dump(self, pkl)
        logger.info('saved object success.')

    @classmethod
    def load_object(cls, filepath: str = 'bili_tickets.pkl'):
        import pickle

        try:
            with open(filepath, 'rb') as pkl:
                obj: cls = pickle.load(pkl)
        except Exception as e:
            raise BiliException(
                'Error happened while loading pkl. Error: {}'.format(e))

        logger.info('load object success. testing cookie...')

        obj._user_cookie = BiliLogin.test_or_get_cookie(obj._user_cookie)

        return obj
