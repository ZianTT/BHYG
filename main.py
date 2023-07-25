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

import os
import time
import threading

from classes import BiliException, BiliTickets
from utils import get_logger_

logger = get_logger_('main.py')

REST_BETWEEN_STARTING_THREADS = 1


def start_threads(obj: BiliTickets, max_thread: int = 1):
    threads: list[threading.Thread] = []
    max_thread = max_thread if 1 <= max_thread <= 3 else 1

    for index in range(max_thread):
        t = threading.Thread(
            target=obj.run,
            name=f'Thread{index}',
            args=(f'Thread{index}', )
        )
        threads.append(t)
        t.start()
        logger.info(f'Thread{index} started')
        time.sleep(REST_BETWEEN_STARTING_THREADS)
        if not threads[0].is_alive():
            exit()

    while True:
        if True in [t.is_alive for t in threads]:
            pass  # wait for other threads.
        else:
            break


def quick_start(max_thread: int = 1):
    logger.info('quick start! max_thread: {}'.format(max_thread))
    obj = BiliTickets.load_object()

    # info
    if hasattr(obj, '_buyers_str'):
        buyer = obj._buyers_str
    else:
        buyer = obj._contant_info
    project = obj._project_name
    ticket = obj._ticket_info_str
    count = obj._tickets_count
    pay_money = obj._pay_money / 100
    info = '\n请检查票务信息\n' + \
        f'[{project}]{ticket} * {count} pcs\n' + \
        f'money: RMB {pay_money} * {count} pcs = RMB {pay_money * count}\n' + \
        f'buyer_info: {buyer}\n'
    print(info)

    try:
        input('检查信息无误后请回车，否则[Ctrl+C]重新配置\t\t>>>\t')
    except KeyboardInterrupt:
        os.remove('bili_tickets.pkl')
        main()

    start_threads(obj, max_thread=max_thread)
    logger.info('threads started.')
    info = info.replace('\n', '\\n')
    logger.info(f'info: {info}')


def main():
    # load/get/init obj
    if os.path.exists('bili_tickets.pkl'):
        logger.info('file `bili_tickets.pkl` found.')
        print('\nfile `bili_tickets.pkl` found.')
        print('[WARNING]【绝·对·不·要】随意加载未知来源的pkl文件!!请确保这个pkl是你之前运行程序时留下的pkl!!')
        input_ = input('载入?(y/n)\t\t>>>\t').lower()

        if input_ == 'y':
            logger.info('user chose to load pkl.')
            obj = BiliTickets.load_object()

        elif input_ == 'n':
            logger.info('user chose NOT to load pkl.')
            obj = BiliTickets()

        else:
            raise BiliException(f'unknown input: {input_}')

    else:
        logger.info('file `bili_tickets.pkl` NOT found. init.')
        obj = BiliTickets()

    # save obj
    input_ = input('初始化/更新完成。是否覆写/创建pkl文件保存配置? (y/n)\t\t>>>\t').lower()
    if input_ == 'y':
        logger.info('user chose to save pkl.')
        obj.save_object()

    elif input_ == 'n':
        logger.info('user chose NOT to save pkl.')

    # threads
    try:
        input_ = input('\n\n初始化完成. 线程数? 留空使用1, [Ctrl+C]不启动抢票线程\t\t>>>\t')
    except KeyboardInterrupt:
        exit()

    num = 1 if not input_ else int(input_)
    start_threads(obj, max_thread=num)


if __name__ == '__main__':
    logger.debug('')
    logger.debug('='*80)

    # quick start?
    if os.path.exists('bili_tickets.pkl'):
        input_ = input('快速启动? 直接回车Yes, 否则No\t\t>>>\t').lower()
        if not input_:
            logger.info('user chose to quick_start.')
            quick_start()
            exit()
    else:
        main()

# CJ 2023   id=74643    REAL_NAME
#           id=75003    NOT_REAL_NAME
