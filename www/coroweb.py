#写在前面
#这一部分也是整段垮掉，完全不晓得各种变量的意义和函数的作用，只能说走一步看一步吧
import asyncio,os,inspect,logging,functools
from aiohttp import web
from urllib import parse
from apis import APIError
# from apis import APIError 还没写

#get方法，是个decorator
def get(path):
    def decorator(func):
        @functools.wraps(func)#保证函数名仍为get
        def wrapper(*args,**kw):
            return func(*args,**kw)
        func.__method__='GET'
        func.__route__=path#这里的两个属性在后面的RequestHandler函数中有使用到
        return wrapper
    return decorator       

#post方法，也是个decorator
def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,*kw)
        func.__method__='POST'
        func.__route__=path
        return wrapper
    return decorator

#获取函数的强制性（且无默认值）参数
def get_required_kw_args(fn):
    args=[]
    params=inspect.signature(fn).parameters
    for name,param in params:
        if param.kind==inspect.Parameter.KEYWORD_ONLY and param.kind==inspect.Parameter.empty:
            args.append(name)
    return tuple(args)#为什么返回元组对象,保证不可更改?

#获取函数的强制性参数
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:#前面有*args参数
            args.append(name)
    return tuple(args)

#判断是否具有强制性参数（前面有*args参数）
def has_named_kw_args(fn):
    params=inspect.signature(fn).parameters
    for name,param in params.items:
        if param.kind==inspect.Parameter.KEYWORD_ONLY:
            return True
    # return False 为什么没有这一句

#判断是否具有VAR_KEYWORD参数（**kw参数）
def has_var_kw_args(fn):
    params=inspect.signature(fn).parameters
    for name,param in params.items:
        if param.kind==inspect.Parameter.VAR_KEYWORD:
            return True

#判断是否含有request参数
def has_request_arg(fn):
    sig=inspect.signature(fn)
    params=sig.parameters
    found=False
    for name,param in params.items():
        if name=='request':
            found=True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
        #上面这一段真的搞不懂，为什么要确保request的位置
    return found

#请求处理类，实现了__call__函数，所以可以当做请求处理函数
#完了完了，都看不懂
class RequestHandler(object):
    def __init__(self,app,fn):
        #定义私有成员变量
        self._app=app
        self._func=fn
        self._has_request_arg=has_request_arg(fn)
        self._has_named_kw_args=has_named_kw_args(fn)
        self._has_var_kw_args=has_var_kw_args(fn)
        self._named_kw_args=get_named_kw_args(fn)
        self._required_kw_args=get_required_kw_args(fn)

    async def __call__(self,request):
        kw=None
        if self._has_var_kw_args or self._has_named_kw_args or self._required_kw_args:
            if request.method=='POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct=request.content_type.lower()
                if ct.startswith('application/json'):
                    params=await request.json()#为啥要异步
                    if not isinstance(params,dict):
                        return web.HTTPBadRequest('JSON body must be object.')#JSON需要是dict对象
                    kw=params
                elif ct.startswith('application/x-www-form-urlencoded')or ct.startswith('multipart/form-data'):#迷惑
                    params=await request.post()
                    kw=dict(**params)#似乎和dict(params)没区别
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method=='GET':
                qs=request.query_string
                if qs:
                    kw=dict()
                    for k,v in parse.parse_qs(qs,True).items():
                        kw[k]=v[0]
        if kw is None:
            kw=dict(**request.match_info)
        else:
            if not self._has_var_kw_args and self._named_kw_args:
                #remove all unamed kw 为啥啊？剔除多余的参数？
                copy=dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name]=kw[name]
                kw=copy
            #check named args:
            for k,v in request.match_info.items():#所以match_info到底是个啥
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k]=v
        if self._has_request_arg:
            kw['request'] = request
        # check required kw:
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)
         