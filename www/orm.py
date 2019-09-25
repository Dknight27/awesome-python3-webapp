#写在前面
#编写orm要从上层调用者的角度考虑问题
import asyncio
import aiomysql
import logging;logging.basicConfig(level=logging.INFO)

def log(sql,args=()):
    logging.info('SQL: %s'%sql)
    
#创建线程池
async def create_pool(loop,**kw):#这里所需的参数都写在config文件里，方便后期修改（内心os：好强啊！）
    logging.info('create database connection...')
    global __pool
    __pool=await aiomysql.create_pool(
        host=kw.get('host','http://172.27.0.3'),
        port=kw.get('port',3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset','utf-8'),
        autocommit=kw.get('autocommit',True),
        maxsize=kw.get('maxsize',10),
        minsize=kw.get('minsize',1),
        loop=loop
    )

async def select(sql,args,size=None):
    log(sql,args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?','%s'),args or ())#使用带参数的sql语句，这样可以防止注入攻击
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s'%len(rs))
        return rs

#执行insert、update、delete操作
async def execute(sql,args,autocommit=True):
    log(sql)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?','%s'),args or ())
                # 重要，就是上面这句代码向表中添加了数据，之前一直疑惑，每次创建一个新的实例，为什么每次都向数据库的
                # 相同表中添加了数据呢？现在看来是通过create_pool绑定数据库，再通过这句代码执行指定的操作，说到底，我还是没有意识到
                # 我所写的，只是一个接口，不是直接实现数据库
                affected=cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected#返回受影响的行数

class Model(dict, metaclass=ModelMetaclass):
    def __init__(self,**kw):
        super(Model,self).__init__(**kw)
    
    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
             raise AttributeError(r"'Model' object has no attribute '%s'" % key)
    
    def __setattr__(self,key,value):
        self[key]=value

    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):
        value=getattr(self,key,None)
        if  value is None:
            field=self.__mappings__[key]
            if field.default is None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self,key,value)
        return value

    @classmethod
    async def find(cls,pk):
        #通过primary key找到对象
        rs=await select('%s where `%s`=?'%(cls.__select__, cls.__primary_key__),[pk],1)
        if len(rs)==0:
            return None
        return cls(**rs[0])#返回了一个包含列表的列表?
    
    @classmethod
    async def findAll(cls,where=None,args=None,**kw):
        sql=[cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args=[]
        orderBy=kw.get('orderBy',None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit=kw.get('limit',None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit,int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit,tuple) and len(limit)==2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs=await select(' '.join(sql),args)
        return [cls(**r) for r in rs]
    
    async def save(self):
        args=list(map(self.getValueOrDefault,self.__fields__))#按照fields顺序的list参数?
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows=await execute(self.__insert__,args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows %s'%rows)

    async def update(self):
        args=list(map(self.getValueOrDefault,self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows=await execute(self.__update__,args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows %s'%rows)

    async def remove(self):
        args=[self.getValue(self.__primary_key__)]#为什么要用list对象
        rows=await execute(self.__delete__,args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)

class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s,%s:%s>'%(self.__class__.__name__,self.column_type,self.name)

class StringField(Field):
    def __init__(self,name=None,primary_key=False,default=None,ddl='varchar(100)'):#为什么没有用到colunm_type呢？
        super.__init__(name,ddl,primary_key,default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

def create_args_string(num):
    L=[]
    for num in range(num):
        L.append('?')
    return ','.join(L)

class ModelMetaclass(type):
    def __new__(cls,name,bases,attrs):
        #排除Model类,但是为什么    续：只是为了不更改Model类
        if __name__ == 'Model':
            return type.__new__(cls,name,bases,attrs)
        #table name
        tableName=attrs.get('__table__',None) or name #默认表名和类名是一样的
        logging.info('found model: %s(table: %s)'%(name,tableName))
        #获取所有的Filed和主键
        mappings=dict()
        fields=[]
        primaryKey=None
        for k,v in attrs.items():
            if isinstance(v,Field):
                logging.info('found mapping: %s ==> %s'%(k,v))
                mappings[k]=v
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey=k
                else:
                    fields.append(k)#不是很懂这有什么用
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        for k in mappings.keys():
            attrs.pop(k)#为什么要pop掉这些属性? 目前已知：对于不存在的属性才会调用__getattr__()
        escaped_fields=list(map(lambda f: '`%s`'%f,fields))#有什么用？
        attrs['__mappings__']=mappings
        attrs['__table__']=tableName
        attrs['__primary_key__']=primaryKey
        attrs['__fields__']=fields
        #构造 默认的 select,update,insert,delete函数
        #整段垮掉，好多看不懂什么意思，流下了没有好好学习数据库的泪水
        attrs['__select__']='select `%s`, %s from %s'%(primaryKey, ','.join(escaped_fields), tableName)
        #这里的insert语句可以确保前后参数的顺序是按照fields+primary_key的顺序来填充的
        attrs['__insert__']='insert into `%s` (%s,`%s`) values(%s)'%(tableName, ','.join(escaped_fields),primaryKey, create_args_string(len(escaped_fields)+1))
        #这个update函数里的lambda函数是不是只是想让我们了解一下，感觉跟上面的没区别啊    续：不，有区别，把%s替换成了%s=?
        attrs['__update__']='update `%s` set %s where `%s`=?'%(tableName,','.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__']='delete from `%s` where `%s`=?'%(tableName,primaryKey)
        return type.__new__(cls,name,bases,attrs)