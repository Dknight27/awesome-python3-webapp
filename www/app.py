#经测试，现在这个程序返回的网页不能被正确解析，原因不明
#表现为：Edge网页显示body中字符串内容（包括标签）
#Google网页返回一个下载
#解决：教程过时，参考aiohttp最新文档
import logging;logging.basicConfig(level=logging.INFO)#打印日志信息

import asyncio,os,json,time
from datetime import datetime

from aiohttp import web

def index(request):
    return web.Response(text='Awesome!')

# 这样封装无法正常运行
# @asyncio.coroutine
# def init():
#     app=web.Application()
#     app.add_routes([web.get('/',index)])
#     # srv=yield from loop.create_server(app.make_handler(),'172.27.0.3',9999)#sh*t,忘了加括号
#     web.run_app(app)
#     logging.info('server started')
#     return app

app = web.Application()
app.add_routes([web.get('/',index)])#对当前ip:8080进行监听
logging.info('server started')
web.run_app(app)