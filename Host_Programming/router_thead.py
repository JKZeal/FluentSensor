import socket
import sqlite3
import struct
import time
from datetime import datetime
import threading
import os  # Added for os.path and os.makedirs

DB_PATH = "db/sqlite.db"


def connect_to_db():
    """
    Connects to the SQLite database and ensures the sensor_data table exists.
    Also creates the database directory if it doesn't exist.
    """
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):  # Only create if dirname is not empty
        os.makedirs(db_dir, exist_ok=True)
        print(f"数据库目录已创建: {db_dir}")

    # Increased timeout for database connection, useful if DB is busy
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS sensor_data
                     (
                         id
                         INTEGER
                         PRIMARY
                         KEY
                         AUTOINCREMENT,
                         timestamp
                         DATETIME
                         NOT
                         NULL,
                         temperature
                         REAL
                         NOT
                         NULL,
                         humidity
                         REAL
                         NOT
                         NULL,
                         pm25
                         INTEGER
                         NOT
                         NULL,
                         noise
                         INTEGER
                         NOT
                         NULL
                     )
                     """)


def save_to_db(data):
    """Saves sensor data to the database."""
    # Each call to save_to_db establishes its own connection, suitable for multi-threading.
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


def unpack_data(packet_bytes):
    """
    Unpacks the raw byte packet into a dictionary of sensor data.
    Expects an 11-byte packet (4-byte header + 7-byte data).
    """
    expected_len = 11  # 4 bytes header + 7 bytes data
    if len(packet_bytes) != expected_len:
        raise ValueError(f"无效的数据包长度. 期望 {expected_len}, 收到 {len(packet_bytes)}.")

    header = packet_bytes[:4]
    if header != b'\xAA\xBB\xCC\xDD':
        raise ValueError(f"无效的头部. 期望 b'\\xAA\\xBB\\xCC\\xDD', 收到 {header.hex()}. 数据包: {packet_bytes.hex()}")

    data_payload = packet_bytes[4:11]  # 7 bytes of data payload

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


def handle_client_connection(client_socket, client_address):
    """
    Handles a single client connection in a dedicated thread.
    Reads packets, unpacks data, and saves to DB.
    """
    thread_id = threading.get_ident()
    print(f"线程 {thread_id}: 处理来自 {client_address} 的连接...")

    PACKET_SIZE = 11  # 4 byte header + 7 byte data
    CLIENT_TIMEOUT = 10.0  # Seconds to wait for data on client socket before assuming idle/timeout

    try:
        client_socket.settimeout(CLIENT_TIMEOUT)

        while True:
            received_data_buffer = b''

            # Loop to ensure the full packet is read
            while len(received_data_buffer) < PACKET_SIZE:
                try:
                    # Read the remaining part of the packet
                    chunk = client_socket.recv(PACKET_SIZE - len(received_data_buffer))
                    if not chunk:
                        # Client closed connection
                        if len(received_data_buffer) == 0:
                            print(f"线程 {thread_id}: 客户端 {client_address} 断开连接 (未发送数据).")
                        else:
                            print(
                                f"线程 {thread_id}: 客户端 {client_address} 在传输数据包中途断开 (收到 {len(received_data_buffer)}/{PACKET_SIZE} 字节).")
                        return  # Exit this client's handler thread
                    received_data_buffer += chunk
                except socket.timeout:
                    # Timeout while waiting for a part of the packet
                    if len(received_data_buffer) == 0:
                        # Timed out waiting for a new packet. This can happen if client is idle.
                        # The outer `while True` will loop, and we'll try `recv` again if CLIENT_TIMEOUT hasn't been hit globally for the connection.
                        # If CLIENT_TIMEOUT is hit, the outer try-except for socket.timeout will catch it.
                        # For now, break inner read loop, outer loop continues to wait.
                        break
                    else:
                        # Timed out in the middle of receiving a packet. This is more serious.
                        print(
                            f"线程 {thread_id}: 从 {client_address} 接收数据包中途超时 (收到 {len(received_data_buffer)}/{PACKET_SIZE} 字节). 连接可能已损坏.")
                        return  # Exit this client's handler thread
                except OSError as e:
                    print(f"线程 {thread_id}: 从 {client_address} 接收数据时发生Socket错误: {e}")
                    return

            if len(received_data_buffer) < PACKET_SIZE:
                # This occurs if the inner loop was broken by a timeout while waiting for the *start* of a packet.
                # In this case, received_data_buffer will be empty. We just continue the main client loop.
                if not received_data_buffer:
                    continue
                else:  # Should not be reached if logic is correct
                    print(
                        f"线程 {thread_id}: 从 {client_address} 收到不完整数据包 ({len(received_data_buffer)}/{PACKET_SIZE} 字节) 后读取循环结束. 丢弃.")
                    continue

            # If we have a full packet
            if len(received_data_buffer) == PACKET_SIZE:
                try:
                    sensor_data = unpack_data(received_data_buffer)
                    print(f"线程 {thread_id}: 接收数据来自 {client_address}: {sensor_data}")
                    save_to_db(sensor_data)
                except ValueError as e:
                    print(f"线程 {thread_id}: 数据包解析错误来自 {client_address}: {e}")
                    print(f"线程 {thread_id}: 因解析错误，关闭与 {client_address} 的连接.")
                    return
                    # Reset buffer for next packet (implicitly done by received_data_buffer = b'' at start of loop)

    except socket.timeout:
        # This timeout is from client_socket.settimeout(CLIENT_TIMEOUT) if no data received for a long time.
        print(f"线程 {thread_id}: 与客户端 {client_address} 长时间无活动，连接超时.")
    except OSError as e:
        print(f"线程 {thread_id}: 与客户端 {client_address} 通信时发生Socket错误: {e}")
    except Exception as e:
        print(f"线程 {thread_id}: 处理客户端 {client_address} 时发生意外错误: {e}")
    finally:
        print(f"线程 {thread_id}: 关闭与 {client_address} 的连接.")
        client_socket.close()


def receive_tcp_data(host='0.0.0.0', port=6000):

    print(f"数据接收服务启动中 ({host}:{port})...")

    try:
        connect_to_db()  # Initialize DB (create table if not exists, and directory)
    except Exception as e:
        print(f"主线程: 数据库初始化失败: {e}. 服务无法启动.")
        return

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((host, port))
        server_socket.listen(5)  # Allow a backlog of up to 5 connections
        server_socket.settimeout(1.0)  # Timeout for accept() to allow KeyboardInterrupt check
        print(f"数据接收服务已启动，监听 {host}:{port}")

        active_client_threads = []

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                print(f"主线程: 新连接：来自 {client_address}")

                # Clean up list of finished threads (optional, but good practice)
                active_client_threads = [t for t in active_client_threads if t.is_alive()]

                client_thread = threading.Thread(
                    target=handle_client_connection,
                    args=(client_socket, client_address),
                    daemon=True  # Daemon threads will exit when the main program exits
                )
                client_thread.start()
                active_client_threads.append(client_thread)
                print(f"主线程: 当前活动客户端线程数: {len(active_client_threads)}")

            except socket.timeout:
                # server_socket.accept() timed out. This is normal, allows loop to process KeyboardInterrupt.
                continue
            except KeyboardInterrupt:
                print("主线程: 服务关闭请求已接收 (KeyboardInterrupt).")
                break
            except Exception as e:
                print(f"主线程: 接受连接或创建线程时出错: {e}")
                time.sleep(1)

    except OSError as e:
        print(f"主线程: 服务启动失败 (bind/listen error): {e}")
    except Exception as e:
        print(f"主线程: 服务发生严重错误: {e}")
    finally:
        print("主线程: 开始关闭服务...")

        # For daemon threads, explicit join is not strictly needed for program exit,
        # but if you wanted to ensure they attempt to finish work:
        # for thread in active_client_threads:
        #     if thread.is_alive():
        #         thread.join(timeout=2.0) # Wait briefly

        if 'server_socket' in locals() and server_socket.fileno() != -1:
            try:
                server_socket.close()
                print("主线程: 数据接收服务套接字已关闭.")
            except Exception as e:
                print(f"主线程: 关闭服务套接字时出错: {e}")
        print("主线程: 数据接收服务已关闭.")


if __name__ == "__main__":
    receive_tcp_data()