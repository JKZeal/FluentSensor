import sqlite3
from datetime import datetime
import socket
import struct

DB_PATH = "sensor_data.db"

def init_db():
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

def unpack_data(packet):
    # 解析头（4 字节）
    header = packet[:4]
    if header != b'\xAA\xBB\xCC\xDD':
        raise ValueError("Invalid header")
    data = packet[4:11]
    # 解析温度（2 字节，int16_t）
    temperature = struct.unpack('>h', data[:2])[0] / 10.0
    # 解析湿度（2 字节，uint16_t）
    humidity = struct.unpack('>H', data[2:4])[0] / 10.0
    # 解析 PM2.5（2 字节，uint16_t）
    pm25 = struct.unpack('>H', data[4:6])[0]
    # 解析噪声（1 字节，uint8_t）
    noise = struct.unpack('>B', data[6:7])[0]
    return {
        "temperature": temperature,
        "humidity": humidity,
        "pm25": pm25,
        "noise": noise
    }

def receive_tcp_data(host='0.0.0.0', port=5000):
    init_db()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Listening on {host}:{port}...")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")

            try:
                while True:
                    packet = client_socket.recv(12)
                    if not packet:
                        break
                    try:
                        sensor_data = unpack_data(packet)
                        print(f"Received: {sensor_data}")
                        save_to_db(sensor_data)
                    except ValueError as e:
                        print(f"Error parsing packet: {e}")
            except Exception as e:
                print(f"Error during communication: {e}")
            finally:
                client_socket.close()
                print(f"Connection to {client_address} closed")
    except KeyboardInterrupt:
        print("Server shutdown requested.")
    finally:
        server_socket.close()
        print("Server closed.")

if __name__ == "__main__":
    receive_tcp_data()
