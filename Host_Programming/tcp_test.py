import socket
import random
import time
import struct


def generate_sensor_data():
    """生成随机的传感器数据"""
    temperature = round(random.uniform(20.0, 30.0), 1)  # 温度范围：20.0°C - 30.0°C
    humidity = round(random.uniform(40.0, 60.0), 1)  # 湿度范围：40.0% - 60.0%
    pm25 = random.randint(0, 100)  # PM2.5范围：0 - 100
    noise = random.randint(30, 70)  # 噪声范围：30 dB - 70 dB
    return {
        "temperature": temperature,
        "humidity": humidity,
        "pm25": pm25,
        "noise": noise
    }


def calculate_checksum(data):
    """计算校验位（简单的累加和校验）"""
    checksum = 0
    for byte in data:
        checksum += byte
    return checksum & 0xFF  # 取低8位


def pack_data(sensor_data):
    """将数据打包为带头和校验位的格式"""
    # 将传感器数据打包为固定格式
    temperature = int(sensor_data["temperature"] * 10)  # 转换为int16_t
    humidity = int(sensor_data["humidity"] * 10)  # 转换为uint16_t
    pm25 = sensor_data["pm25"]  # uint16_t
    noise = sensor_data["noise"]  # uint8_t

    # 打包数据
    data = struct.pack('>h H H B', temperature, humidity, pm25, noise)

    # 添加头（4字节，固定为0xAA 0xBB 0xCC 0xDD）
    header = b'\xAA\xBB\xCC\xDD'

    # 计算校验位
    checksum = calculate_checksum(data)

    # 打包数据：头 + 数据 + 校验位
    packet = header + data + bytes([checksum])
    return packet


def send_tcp_data(host='127.0.0.1', port=5000):
    """发送TCP数据包"""
    # 创建TCP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # 连接到服务器
        client_socket.connect((host, port))
        print(f"Connected to {host}:{port}")

        while True:
            # 生成传感器数据
            sensor_data = generate_sensor_data()
            # 打包数据
            packet = pack_data(sensor_data)
            # 发送数据
            client_socket.sendall(packet)
            print(f"Sent: {sensor_data}")
            # 等待5秒
            time.sleep(5)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # 关闭连接
        client_socket.close()
        print("Connection closed")


if __name__ == "__main__":
    # 设置目标IP和端口
    target_host = '127.0.0.1'  # 目标IP地址
    target_port = 5000  # 目标端口
    send_tcp_data(target_host, target_port)
