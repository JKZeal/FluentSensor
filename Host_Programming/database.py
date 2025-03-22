import sqlite3
from datetime import datetime

# 数据库路径
DB_PATH = "sensor_data.db"

def init_db():
    """初始化数据库表结构"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                pm25 INTEGER NOT NULL,
                noise INTEGER NOT NULL
            )
        """)

def save_to_db(data):
    """将数据保存到数据库"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO sensor_data 
            (timestamp, temperature, humidity, pm25, noise)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data['temperature'],
            data['humidity'],
            data['pm25'],
            data['noise']
        ))
