import tkinter as tk
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体为 SimHei
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 数据库路径
DB_PATH = "sensor_data.db"


class SensorMonitorApp:
    def __init__(self, root, refresh_interval=5000):
        self.root = root
        self.refresh_interval = refresh_interval

        # 初始化界面
        self.setup_ui()

        # 启动定时刷新
        self.update_charts()

    def setup_ui(self):
        """初始化用户界面"""
        self.root.title("传感器数据实时监控")
        self.root.geometry("800x600")

        # 创建Matplotlib图形
        self.fig, self.axes = plt.subplots(4, 1, figsize=(8, 6))
        self.fig.subplots_adjust(hspace=0.5)

        # 将图形嵌入到Tkinter窗口
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 初始化子图
        self.lines = {}
        self.init_subplot(self.axes[0], "温度 (℃)", "temperature", 'r')
        self.init_subplot(self.axes[1], "湿度 (%)", "humidity", 'b')
        self.init_subplot(self.axes[2], "PM2.5 (μg/m³)", "pm25", 'g')
        self.init_subplot(self.axes[3], "噪声 (dB)", "noise", 'purple')

    def init_subplot(self, ax, title, key, color):
        """初始化单个子图"""
        ax.set_title(title)
        ax.set_xlabel("时间")
        ax.set_ylabel(title.split()[0])
        ax.grid(True)
        line, = ax.plot([], [], color=color)
        self.lines[key] = line

    def update_charts(self):
        """更新所有图表"""
        data = self.fetch_recent_data(minutes=5)  # 获取最近5分钟数据

        # 更新每个子图
        for key, line in self.lines.items():
            timestamps = [datetime.strptime(d['timestamp'], "%Y-%m-%d %H:%M:%S") for d in data]
            values = [d[key] for d in data]
            line.set_data(timestamps, values)
            ax = line.axes

            # 调整X轴范围
            if timestamps:
                ax.set_xlim(min(timestamps), max(timestamps))

            # 调整Y轴范围
            if values:
                ax.set_ylim(min(values) * 0.9, max(values) * 1.1)

        # 重绘画布
        self.canvas.draw()

        # 安排下次更新
        self.root.after(self.refresh_interval, self.update_charts)

    def fetch_recent_data(self, minutes=5):
        """从数据库获取最近的数据"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sensor_data
                WHERE timestamp >= datetime('now', ?)
                ORDER BY timestamp ASC
            """, (f"-{minutes} minutes",))

            return [
                {
                    "timestamp": row[1],
                    "temperature": row[2],
                    "humidity": row[3],
                    "pm25": row[4],
                    "noise": row[5]
                }
                for row in cursor.fetchall()
            ]


if __name__ == "__main__":
    # 初始化数据库（确保表结构存在）
    with sqlite3.connect(DB_PATH) as conn:
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

    # 启动GUI
    root = tk.Tk()
    app = SensorMonitorApp(root)
    root.mainloop()
