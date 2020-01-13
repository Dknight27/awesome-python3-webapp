# config_default.py

configs = {
    'db': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'admin',
        'database': 'awesome'
    },
    'session': {
        'secret': 'Awesome'#这个有什么用 续：用于cookie的生成
    }
}