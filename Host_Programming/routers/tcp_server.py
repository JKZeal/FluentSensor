import socket
import threading
from shared.data_bus import data_bus
from config.protocol import unpack_data


def start_tcp_server(host='127.0.0.1', port=5000):
    def client_handler(client_socket):
        while True:
            packet = client_socket.recv(1024)
            if packet:
                try:
                    sensor_data = unpack_data(packet)
                    print(f"Received: {sensor_data}")
                    data_bus.put_data(sensor_data)  # 数据存入总线
                except ValueError as e:
                    print(f"Parse error: {e}")
            else:
                break

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)

    print(f"TCP Server started at {host}:{port}")

    while True:
        client_sock, addr = server_socket.accept()
        print(f"Client connected from {addr}")
        client_thread = threading.Thread(
            target=client_handler,
            args=(client_sock,),
            daemon=True
        )
        client_thread.start()


# 在独立线程启动服务器
def run_server():
    server_thread = threading.Thread(
        target=start_tcp_server,
        daemon=True
    )
    server_thread.start()
