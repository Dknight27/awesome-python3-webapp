def outer(func):
    print(100)
    def inner():
        
        return func()
    return inner

@outer
def new():
    pass
