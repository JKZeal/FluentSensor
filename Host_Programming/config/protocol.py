import json
import struct


def calculate_checksum(data):
    """计算校验位（简单的累加和校验）"""
    checksum = 0
    for byte in data:
        checksum += byte
    return checksum & 0xFF  # 取低8位


def pack_data(sensor_data):
    """将数据打包为带头和校验位的格式"""
    # 将数据转换为JSON字符串
    data_json = json.dumps(sensor_data)
    # 将JSON字符串编码为字节
    data_bytes = data_json.encode('utf-8')
    # 添加头（4字节，固定为0xAA 0xBB 0xCC 0xDD）
    header = bytes([0xAA, 0xBB, 0xCC, 0xDD])
    # 计算校验位
    checksum = calculate_checksum(data_bytes)
    # 打包数据：头 + 数据长度（2字节） + 数据 + 校验位
    packet = header + struct.pack('>H', len(data_bytes)) + data_bytes + bytes([checksum])
    return packet


def unpack_data(packet):
    """解析带头和校验位的数据包"""
    # 解析头（4字节）
    header = packet[:4]
    if header != bytes([0xAA, 0xBB, 0xCC, 0xDD]):
        raise ValueError("Invalid header")
    # 解析数据长度（2字节）
    data_length = struct.unpack('>H', packet[4:6])[0]
    # 解析数据
    data_bytes = packet[6:6 + data_length]
    # 解析校验位（1字节）
    checksum = packet[-1]
    # 验证校验位
    if calculate_checksum(data_bytes) != checksum:
        raise ValueError("Checksum verification failed")
    # 将数据解码为JSON
    data_json = data_bytes.decode('utf-8')
    sensor_data = json.loads(data_json)
    return sensor_data
