import socket
import struct
import csv
from datetime import datetime
from database import init_db, save_to_db  # 导入数据库工具

def calculate_checksum(data):
    # 计算校验位（累加和校验）
    checksum = 0
    for byte in data:
        checksum += byte
    return checksum & 0xFF  # 取低 8 位

def unpack_data(packet):
    # 解析头（4 字节）
    header = packet[:4]
    if header != b'\xAA\xBB\xCC\xDD':
        raise ValueError("Invalid header")
    data = packet[4:11]
    checksum = packet[11]
    if calculate_checksum(data) != checksum:
        raise ValueError("Checksum verification failed")
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

def save_to_csv(data, filename="sensor_data.csv"):
    """保存数据到CSV文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_with_timestamp = {"timestamp": timestamp, **data}

    # 写入 CSV 文件
    with open(filename, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["timestamp", "temperature", "humidity", "pm25", "noise"])
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(data_with_timestamp)

def receive_tcp_data(host='127.0.0.1', port=5000):
    # 初始化数据库
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
                    # 解析数据包
                    try:
                        sensor_data = unpack_data(packet)
                        print(f"Received: {sensor_data}")
                        save_to_csv(sensor_data)  # 保存到CSV
                        save_to_db(sensor_data)   # 保存到数据库
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
