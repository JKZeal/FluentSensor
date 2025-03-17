import socket
import os
import sys
import json

# 导入协议模块
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from config.protocol import unpack_data


def save_data_to_file(data_list, filename='../database/sensor_data.json'):
    """将数据列表保存到文件（JSON格式追加写入）"""
    # 确保路径正确
    file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), filename))
    file_exists = os.path.isfile(file_path)

    # 打开文件，以追加模式写入
    with open(file_path, 'a') as f:
        if not file_exists:
            # 如果文件不存在，写入文件开头的 JSON 数组起始符
            f.write('[\n')
        else:
            # 如果文件已存在，补充逗号以维持 JSON 数组的格式
            f.write(',\n')
        # 写入数据列表
        for i, data in enumerate(data_list):
            json.dump(data, f, indent=4)
            if i < len(data_list) - 1:
                f.write(',\n')  # 多条数据之间用逗号分隔
    print(f"Data saved to {file_path}")


def start_tcp_server(host='127.0.0.1', port=5000, save_interval=10):
    """启动TCP服务器，累计接收一定数量的数据包后自动保存"""
    # 创建TCP/IP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 绑定socket到端口
    server_socket.bind((host, port))

    # 监听连接
    server_socket.listen(1)
    print(f"Listening on {host}:{port}...")

    # 缓存接收到的数据
    data_buffer = []

    try:
        while True:
            # 等待连接
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")

            try:
                while True:
                    # 接收数据
                    packet = client_socket.recv(1024)
                    if packet:
                        try:
                            # 解析数据包
                            sensor_data = unpack_data(packet)
                            print(f"Received: {sensor_data}")
                            # 将数据添加到缓冲区
                            data_buffer.append(sensor_data)
                            # 检查是否达到保存阈值
                            if len(data_buffer) >= save_interval:
                                save_data_to_file(data_buffer)
                                data_buffer = []  # 清空缓冲区
                        except ValueError as e:
                            print(f"Error parsing packet: {e}")
                    else:
                        break
            except Exception as e:
                print(f"Error: {e}")
            finally:
                # 关闭连接
                client_socket.close()
                print("Connection closed")
    except KeyboardInterrupt:
        # 捕获 Ctrl+C，保存剩余数据并关闭 JSON 文件
        if data_buffer:
            save_data_to_file(data_buffer)
        # 如果需要完善 JSON 文件格式，可以在此处添加逻辑
        print("Server stopped manually.")
start_tcp_server(save_interval=10)