import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体为 SimHei
plt.rcParams['axes.unicode_minus'] = False
from shared.data_bus import data_bus


class SensorDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("环境监测仪表盘")

        # 初始化UI组件
        self.setup_layout()
        self.setup_charts()
        self.start_updater()

    def setup_layout(self):
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 状态栏
        self.status_var = tk.StringVar()
        ttk.Label(
            self.main_frame,
            textvariable=self.status_var,
            anchor='w'
        ).pack(fill=tk.X)

    def setup_charts(self):
        # 创建图表框架
        fig, self.axes = plt.subplots(2, 2, figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 初始化折线图
        self.lines = {
            'temp': self.axes[0, 0].plot([], [], 'r-')[0],
            'humi': self.axes[0, 1].plot([], [], 'b-')[0],
            'pm25': self.axes[1, 0].plot([], [], 'g-')[0],
            'noise': self.axes[1, 1].plot([], [], 'y-')[0]
        }

        # 配置图表样式
        for ax, title in zip(self.axes.flat,
                             ['温度(℃)', '湿度(%)', 'PM2.5', '噪声(dB)']):
            ax.set_title(title)
            ax.grid(True)

    def start_updater(self):
        # 启动50ms间隔的更新定时器
        self._update_display()

    def _update_display(self):
        # 从数据总线获取最新数据
        latest = data_bus.get_latest()

        if latest:
            # 更新折线图数据
            xdata = list(range(len(data_bus._sensor_data)))

            self.lines['temp'].set_data(xdata,
                                        [d['temperature'] for d in data_bus._sensor_data])
            self.lines['humi'].set_data(xdata,
                                        [d['humidity'] for d in data_bus._sensor_data])
            self.lines['pm25'].set_data(xdata,
                                        [d['pm25'] for d in data_bus._sensor_data])
            self.lines['noise'].set_data(xdata,
                                         [d['noise'] for d in data_bus._sensor_data])

            # 自动调整坐标轴范围
            for ax in self.axes.flat:
                ax.relim()
                ax.autoscale_view()

            # 更新图表
            self.canvas.draw()

            # 更新状态栏
            self.status_var.set(
                f"最新数据 | 温度: {latest['temperature']}℃ | "
                f"湿度: {latest['humidity']}% | "
                f"PM2.5: {latest['pm25']} μg/m³ | "
                f"噪声: {latest['noise']}dB"
            )

        # 每50ms触发一次更新
        self.root.after(50, self._update_display)


if __name__ == "__main__":
    from routers.tcp_server import run_server

    root = tk.Tk()
    root.geometry("800x600")

    run_server()  # 启动后台TCP服务器
    app = SensorDashboard(root)
    root.mainloop()
