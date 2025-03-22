import struct

def calculate_checksum(data):
    """计算校验位（简单的累加和校验）"""
    checksum = 0
    for byte in data:
        checksum += byte
    return checksum & 0xFF  # 取低8位

def unpack_data(packet):
    """
    解析固定长度的数据包
    :param packet: 数据包，格式为：头（4字节） + 数据（7字节） + 校验位（1字节）
    :return: 解析后的传感器数据（字典格式）
    """
    # 解析头（4字节）
    header = packet[:4]
    if header != b'\xAA\xBB\xCC\xDD':
        raise ValueError("Invalid header")
    data = packet[4:11]
    checksum = packet[11]
    if calculate_checksum(data) != checksum:
        raise ValueError("Checksum verification failed")
    # 解析温度（2字节，int16_t）
    temperature = struct.unpack('>h', data[:2])[0] / 10.0
    # 解析湿度（2字节，uint16_t）
    humidity = struct.unpack('>H', data[2:4])[0] / 10.0
    # 解析PM2.5（2字节，uint16_t）
    pm25 = struct.unpack('>H', data[4:6])[0]
    # 解析噪声（1字节，uint8_t）
    noise = struct.unpack('>B', data[6:7])[0]
    return {
        "temperature": temperature,
        "humidity": humidity,
        "pm25": pm25,
        "noise": noise
    }

# 示例数据包（来自STM32）
sensor_packet = b'\xAA\xBB\xCC\xDD\x00\xFA\x00\x5D\x00\x32\x4B\x5D'  # 温度: 25.0℃, 湿度: 60.5%, PM2.5: 50 µg/m³, 噪声: 75 dB

# 解析数据包
try:
    sensor_data = unpack_data(sensor_packet)
    print("Sensor Data:", sensor_data)
except ValueError as e:
    print("Error:", e)
