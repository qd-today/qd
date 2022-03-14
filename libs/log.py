#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: A76yyyy<q981331502@163.com>
#         http://www.a76yyyy.cn
# Created on 2022-03-14 11:39:57

import logging
from config import debug
import time
import sys,os
import tornado.log

class Log(object):
    '''
        封装后的logging
    '''
    def __init__(self , logger = None, log_dir_path = None, channel_level = None):
        '''
            指定保存日志的文件路径，日志级别，以及调用文件
            将日志存入到指定的文件中
        '''

        # 创建一个logger
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.logger.propagate = False
        
        # 创建一个handler，用于写入日志文件
        self.log_time = time.strftime("%Y_%m_%d")

        # 定义handler的输出格式
        formatter = tornado.log.LogFormatter()

        self.logger.handlers.clear()
        
        # 创建一个handler，用于输出到控制台
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        if channel_level:
            ch.setLevel(channel_level)
        else:
            ch.setLevel(logging.DEBUG if debug else logging.INFO)

        # 给logger添加handler
        self.logger.addHandler(ch)

        if log_dir_path:
            self.logger.propagate = True
            self.log_name = os.path.join(log_dir_path,self.log_time + '.log')
            fh = logging.FileHandler(self.log_name, 'a', encoding='utf-8')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def getlogger(self):
        return self.logger