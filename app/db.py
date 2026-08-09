import psycopg2
from psycopg2.extras import RealDictCursor
import time
# Connecting Database
while True:
    try:
        conn = psycopg2.connect(host='localhost', database='rental', user='postgres', password='1234', cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        print('Successfully connected database')
        break
    except Exception as error:
        print('Database connection Failed!!!!!!!')
        print("Error:", error)
        time.sleep(2)

def homePage():
    cursor.execute(
        """
        select * from user_main
        """
    )
    data = cursor.fetchall()
    return {"Hello": data}