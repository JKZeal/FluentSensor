from queue import Queue
from threading import Lock


class DataBus:
    def __init__(self):
        self._sensor_data = []
        self._raw_queue = Queue()
        self.lock = Lock()

    def put_data(self, data):
        with self.lock:
            self._raw_queue.put(data)
            self._sensor_data.append(data)

    def get_latest(self):
        with self.lock:
            return self._sensor_data[-1] if self._sensor_data else None

    def queue_size(self):
        return self._raw_queue.qsize()


# 单例模式实例化
data_bus = DataBus()
