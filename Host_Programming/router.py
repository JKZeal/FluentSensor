import socket
import sqlite3
import struct
import time
from datetime import datetime

DB_PATH = "db/sqlite.db"

def connect_to_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
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
    print(f"数据接收服务启动中 ({host}:{port})...")
    connect_to_db()

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 设置SOL_SOCKET和SO_REUSEADDR选项，以便服务可以快速重启
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(1)
        # 设置超时，以便能够响应中断
        server_socket.settimeout(1.0)
        print(f"数据接收服务已启动，监听 {host}:{port}")

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                print(f"新连接：来自 {client_address}")

                try:
                    # 设置客户端连接超时
                    client_socket.settimeout(1.0)
                    while True:
                        try:
                            packet = client_socket.recv(12)
                            if not packet:
                                break
                            try:
                                sensor_data = unpack_data(packet)
                                print(f"接收数据: {sensor_data}")
                                save_to_db(sensor_data)
                            except ValueError as e:
                                print(f"数据包解析错误: {e}")
                        except socket.timeout:
                            # 接收超时，继续下一次尝试
                            continue
                        except Exception as e:
                            print(f"接收数据出错: {e}")
                            break
                except Exception as e:
                    print(f"处理连接时出错: {e}")
                finally:
                    client_socket.close()
                    print(f"连接已关闭: {client_address}")
            except socket.timeout:
                # 接受连接超时，继续循环等待
                continue
            except Exception as e:
                print(f"接受连接时出错: {e}")
                # 等待一会再继续尝试
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("服务关闭请求已接收")
    except Exception as e:
        print(f"服务发生错误: {e}")
    finally:
        try:
            server_socket.close()
            print("数据接收服务已关闭")
        except:
            pass

if __name__ == "__main__":
    receive_tcp_data()