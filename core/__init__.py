from db import Db

db = Db(
    host="localhost",
    port=5984,
    database='test',
    username='admin',
    password='password'
)