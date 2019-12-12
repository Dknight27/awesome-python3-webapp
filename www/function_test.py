import functools
def get(path):
    def decorator(func):
        func.__method__='GET'#需要在wrapper使用func之前修改func属性
        func.__route__=path#这里的两个属性在后面的RequestHandler函数中有使用到
        @functools.wraps(func)#保证函数名仍为gets
        def wrapper(*args,**kw):
            print(func)
            return func(*args,**kw)
        print(func)
        return wrapper
    return decorator   

@get('/')
def test():
    pass
print(test.__method__)