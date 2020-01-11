import asyncio
import orm
from models import User,Blog,Comment

async def test(loop):
    await orm.create_pool(loop,user='root',password='admin',db='awesome')
    # u=User(name='王铁柱', email='tiezhuwang@163.com', passwd='1234567890', image='about:blank')
    user=await User.findAll('email=? ',['test@example.com'])
    print(user[0].name)
    # await u.save()

if __name__ == "__main__":
    loop=asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
    print('Test end')
    loop.close()
