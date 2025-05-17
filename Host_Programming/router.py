import socket
import sqlite3
import struct
import time
from datetime import datetime
import os

ESP_TARGET_IP = "192.168.4.1"
ESP_TARGET_PORT = 6666

DB_PATH = "db/sqlite.db"  # 数据库文件路径
PACKET_SIZE = 11          # 预期的数据包大小 (4字节头部 + 7字节数据)
CLIENT_CONNECT_TIMEOUT = 10.0  # 连接到服务器的超时时间 (秒)
CLIENT_RECV_TIMEOUT = 30.0     # 从服务器接收数据的超时时间 (秒)
RECONNECT_DELAY = 5.0          # 连接失败或断开后，重新尝试连接的延迟时间 (秒)

def connect_to_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except OSError as e:
            print(f"创建数据库失败 {db_dir}: {e}")
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            conn.execute("PRAGMA journal_mode=WAL") # 启用WAL模式以获得更好的并发性能
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS sensor_data
                         (
                             id INTEGER PRIMARY KEY AUTOINCREMENT,
                             timestamp DATETIME NOT NULL,
                             temperature REAL NOT NULL,
                             humidity REAL NOT NULL,
                             pm25 INTEGER NOT NULL,
                             noise INTEGER NOT NULL
                         )
                         """)
    except sqlite3.Error as e:
        print(f"数据库操作错误: {e}")
        raise

def save_to_db(data):
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
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
    except sqlite3.Error as e:
        print(f"保存数据到数据库时出错: {e}")



def unpack_data(packet_bytes):
    expected_len = PACKET_SIZE
    if len(packet_bytes) != expected_len:
        raise ValueError(f"无效的数据包长度. 期望 {expected_len}, 收到 {len(packet_bytes)}.")
    header = packet_bytes[:4]
    if header != b'\xAA\xBB\xCC\xDD':
        raise ValueError(f"无效的头部. 期望 b'\\xAA\\xBB\\xCC\\xDD', 收到 {header.hex()}.")
    data_payload = packet_bytes[4:11]
    try:
        temperature = struct.unpack('>h', data_payload[0:2])[0] / 10.0
        humidity = struct.unpack('>H', data_payload[2:4])[0] / 10.0
        pm25 = struct.unpack('>H', data_payload[4:6])[0]
        noise = struct.unpack('>B', data_payload[6:7])[0]
    except struct.error as e:
        raise ValueError(f"解析数据负载时出错: {e}. 负载: {data_payload.hex()}")

    return {
        "temperature": temperature,
        "humidity": humidity,
        "pm25": pm25,
        "noise": noise
    }


def run_tcp_client(server_ip, server_port):
    try:
        connect_to_db()
    except Exception as e:
        print(f"关键错误: 数据库初始化失败: {e}. 程序无法继续。")
        return

    client_socket = None

    while True:
        try:
            print(f"尝试连接到下位机 {server_ip}:{server_port}...")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(CLIENT_CONNECT_TIMEOUT)
            client_socket.connect((server_ip, server_port))
            print(f"成功连接到下位机 {server_ip}:{server_port}")
            client_socket.settimeout(CLIENT_RECV_TIMEOUT)

            while True:
                received_data_buffer = b''
                bytes_to_read = PACKET_SIZE

                while len(received_data_buffer) < PACKET_SIZE:
                    try:
                        chunk = client_socket.recv(bytes_to_read - len(received_data_buffer))
                        if not chunk:
                            raise ConnectionAbortedError("Server closed connection gracefully")
                        received_data_buffer += chunk
                    except socket.timeout:
                        if received_data_buffer:
                             print(f"接收数据包中途超时 (已收到 {len(received_data_buffer)}/{PACKET_SIZE} 字节). 连接可能已损坏.")
                             raise socket.timeout
                        else:
                            pass

                # 处理完整的数据包
                if len(received_data_buffer) == PACKET_SIZE:
                    try:
                        sensor_data = unpack_data(received_data_buffer)
                        print(f"接收数据来自 {server_ip}: {sensor_data} (时间: {datetime.now().strftime('%H:%M:%S')})")
                        save_to_db(sensor_data)
                    except ValueError as e:
                        print(f"数据包解析错误来自 {server_ip}: {e}")


        except socket.timeout:
            print(f"连接或接收数据超时。")
        except ConnectionRefusedError:
            print(f"连接被 {server_ip}:{server_port} 拒绝。请确保下位机服务器已启动并监听。")
        except ConnectionAbortedError as e:
            print(f"连接被中止: {e}。")
        except OSError as e:
            print(f"网络错误: {e}。请检查网络连接和服务器状态。")
        except Exception as e:
            print(f"处理与 {server_ip} 通信时发生意外错误: {e}")
        finally:
            if client_socket:
                client_socket.close()
            print(f"等待 {RECONNECT_DELAY} 秒后重试连接...")
            time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    run_tcp_client(ESP_TARGET_IP, ESP_TARGET_PORT)