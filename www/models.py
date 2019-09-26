import time, uuid

from orm import Model,TextField,FloatField,StringField,BooleanField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)#这个是真的看不懂 续：uuid--通用识别码

class User(Model):
    __table__='users'#表名为users

    #接下来开始定义列
    id=StringField(primary_key=True,default=next_id(),ddl='varchar(50)')#这里的default能确保id的唯一性
    email=StringField(ddl='varchar(50)')
    passwd=StringField(ddl='varchar(50)')
    admin=BooleanField()#是否为管理员，默认为False
    name=StringField(ddl='varchar(50)')
    image=StringField(ddl='varchar(500)')#这是头像吗？为什么要用varchar来存储,存储成网址？
    created_at=FloatField(default=time.time)

class Blog(Model):#这里用来保存博客？
    __table__='blogs'#表名为blogs

    id=StringField(primary_key=True,default=next_id(),ddl='varchar(50)')
    user_id=StringField('varchar(50)')
    user_name=StringField('varchar(50)')
    user_image=StringField('varchar(500)')
    name=StringField('varchar(50)')#name和user_name有什么区别呢
    summary=StringField('varchar(200)') 
    content=TextField()
    created_at=FloatField(default=time.time)

class Comment(Model):
    __table__='comments'

    id=StringField(primary_key=True,default=next_id(),ddl='varchar(50)')
    blog_id=StringField(ddl='varchar(50)')
    user_id=StringField(ddl='varchar(50)')
    user_name=StringField(ddl='varchar(50)')
    user_image=StringField(ddl='varchar(500)')
    content=TextField()
    created_at=FloatField(default=time.time)
